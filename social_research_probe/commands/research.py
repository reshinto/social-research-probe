"""Research command: run the research pipeline from the CLI."""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from social_research_probe.config import load_active_config
from social_research_probe.technologies.llms.registry import get_runner
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.types import RunnerName


@dataclass(frozen=True)
class _ResearchArgs:
    """Normalized research arguments from the CLI.

    Attributes:
        platform: Target platform (for example, "youtube").
        topic: Topic string. Empty when a natural-language query is used.
        purposes: Tuple of purposes. Empty when a query is used.
        query: Natural-language query. Empty when topic and purposes are used.
    """

    platform: str
    topic: str
    purposes: tuple[str, ...]
    query: str


def _structured_runner_order(preferred: RunnerName) -> list[RunnerName]:
    candidates: list[RunnerName] = ["claude", "gemini", "codex", "local"]
    if preferred == "none":
        return []
    return [preferred, *[name for name in candidates if name != preferred]]


def _stage_flag(cfg, name: str, *, default: bool) -> bool:
    fn = getattr(cfg, "stage_enabled", None)
    if fn is None:
        return default
    try:
        return bool(fn(name))
    except Exception:
        return default


def _service_flag(cfg, name: str, *, default: bool) -> bool:
    fn = getattr(cfg, "service_enabled", None)
    if fn is None:
        return default
    try:
        return bool(fn(name))
    except Exception:
        return default


def _run_required_synthesis(packet: dict) -> dict | None:
    from social_research_probe.services.synthesizing.llm_contract import (
        SYNTHESIS_JSON_SCHEMA,
        build_synthesis_prompt,
        parse_synthesis_response,
    )
    from social_research_probe.utils.display.progress import log

    cfg = load_active_config()
    if not _stage_flag(cfg, "synthesis", default=True):
        log("[srp] synthesis: disabled (stages.synthesis = false).")
        return None
    if not _service_flag(cfg, "llm", default=True):
        log(
            "[srp] synthesis: disabled (services.llm = false). Enable the LLM service to allow synthesis."
        )
        return None
    preferred = cfg.default_structured_runner
    if preferred == "none":
        log(
            "[srp] synthesis: disabled (llm.runner = 'none'). Set via 'srp config set llm.runner claude|gemini|codex|local'."
        )
        return None

    prompt = build_synthesis_prompt(packet)
    failures: list[str] = []
    runners = _structured_runner_order(preferred)
    for i, runner_name in enumerate(runners, start=1):
        if hasattr(cfg, "technology_enabled") and not cfg.technology_enabled(runner_name):
            log(f"[srp] synthesis: runner={runner_name} outcome=disabled_by_config")
            failures.append(f"{runner_name}: disabled by technologies.{runner_name}")
            continue
        log(f"[srp] synthesis: attempting runner {i}/{len(runners)} ({runner_name})")
        try:
            runner = get_runner(runner_name)
            if not runner.health_check():
                log(
                    f"[srp] synthesis: runner={runner_name} outcome=unavailable (binary not on PATH)"
                )
                failures.append(f"{runner_name}: unavailable")
                continue
            raw = runner.run(prompt, schema=SYNTHESIS_JSON_SCHEMA)
            result = parse_synthesis_response(raw)
            log(f"[srp] synthesis: runner={runner_name} outcome=success")
            return result
        except ValidationError as exc:
            log(f"[srp] synthesis: runner={runner_name} outcome=invalid_response err={exc}")
            failures.append(f"{runner_name}: invalid response ({exc})")
        except Exception as exc:
            log(f"[srp] synthesis: runner={runner_name} outcome=error err={exc}")
            failures.append(f"{runner_name}: {exc}")
    detail = "; ".join(failures) if failures else "no runners were attempted"
    log(
        "[srp] synthesis: all runners failed — "
        "Compiled Synthesis, Opportunity Analysis, and Final Summary will be omitted. "
        f"failures=[{detail}]"
    )
    return None


def _attach_synthesis(packet: dict) -> None:
    children = packet.get("multi")
    if isinstance(children, list):
        for child in children:
            synthesis = _run_required_synthesis(child)
            if synthesis is not None:
                child.update(synthesis)
        return
    synthesis = _run_required_synthesis(packet)
    if synthesis is not None:
        packet.update(synthesis)


def _resolve_topic_and_purposes(
    research_args: _ResearchArgs,
    data_dir: Path,
    cfg: object,
) -> tuple[str, tuple[str, ...]]:
    from social_research_probe.commands.nl_query import classify_query
    from social_research_probe.utils.display.progress import log

    if research_args.query:
        classified = classify_query(research_args.query, data_dir=data_dir, cfg=cfg)
        log(
            f'[srp] query mapped to topic="{classified.topic}" purpose="{classified.purpose_name}"'
            f" (new topic: {'yes' if classified.topic_created else 'no'},"
            f" new purpose: {'yes' if classified.purpose_created else 'no'})"
        )
        return classified.topic, (classified.purpose_name,)
    return research_args.topic, research_args.purposes


def _log_synthesis_runner_status(cfg: object) -> None:
    from social_research_probe.utils.display.progress import log

    if not _stage_flag(cfg, "synthesis", default=True):
        log("[srp] synthesis: disabled (stages.synthesis = false).")
        return
    if not _service_flag(cfg, "llm", default=True):
        log(
            "[srp] synthesis: disabled (services.llm = false). Enable the LLM service to allow synthesis."
        )
        return
    preferred = cfg.default_structured_runner
    if preferred == "none":
        log(
            "[srp] synthesis: disabled (llm.runner = 'none'). Set via 'srp config set llm.runner claude|gemini|codex|local'."
        )
    else:
        runner = get_runner(preferred)
        if not runner.health_check():
            log(
                "[srp] synthesis: runner "
                f"'{preferred}' binary not found on PATH — synthesis will be skipped."
            )


def _write_final_report(packet: dict, data_dir: Path, cfg, *, allow_html: bool) -> str:
    """Write the final report and return an access path or command.

    Always produces a report file. Markdown output is used as a fallback
    when HTML generation is disabled or fails, ensuring a consistent
    output contract.
    """
    from social_research_probe.services.synthesizing.formatter import render_full
    from social_research_probe.technologies.report_render.html.raw_html.youtube import (
        serve_report_command,
        write_html_report,
    )

    html_on = (
        allow_html
        and _stage_flag(cfg, "report", default=True)
        and _service_flag(cfg, "html_report", default=True)
        and "multi" not in packet
    )
    if html_on:
        try:
            path = write_html_report(
                packet,
                data_dir,
                prepare_voicebox_audio=_service_flag(cfg, "audio_report", default=True),
            )
            uri = path.resolve().as_uri()
            packet["html_report_path"] = uri
            command = serve_report_command(path)
            packet["html_report_command"] = command
            return command
        except Exception:
            pass
    md_path = data_dir / "report.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        body = render_full(packet) if "multi" not in packet else "# Report\n\n_(no content)_\n"
    except Exception:
        body = "# Report\n\n_(no content — every feature disabled or pipeline empty)_\n"
    md_path.write_text(body, encoding="utf-8")
    return str(md_path.resolve())


def _parse_simple_research_args(positional: list[str]) -> _ResearchArgs:
    """Parse positional CLI arguments into structured research arguments.

    Supports both:
        - Classic form: [platform] topic purposes
        - Natural-language query form: [platform] query
    """
    known_platforms = {"youtube"}
    if positional[0] in known_platforms:
        platform = positional[0]
        rest = positional[1:]
    else:
        platform = "youtube"
        rest = positional

    if len(rest) == 0:
        raise ValidationError(
            "research needs at least TOPIC and PURPOSES (or a natural-language query)"
        )

    if len(rest) == 1:
        return _ResearchArgs(platform=platform, topic="", purposes=(), query=rest[0])

    topic, purpose_arg = rest[0], rest[1]
    purposes = tuple(p.strip() for p in purpose_arg.split(",") if p.strip())
    if not purposes:
        raise ValidationError("research needs at least one purpose")
    return _ResearchArgs(platform=platform, topic=topic, purposes=purposes, query="")


def run(args: argparse.Namespace, data_dir: Path) -> int:
    """Execute the research pipeline for the 'research' subcommand."""
    from social_research_probe.commands import DslCommand, parse
    from social_research_probe.pipeline import run_research

    research_args = _parse_simple_research_args(args.args)
    config_extras = {
        "include_shorts": not args.no_shorts,
        "fetch_transcripts": not args.no_transcripts,
    }
    cfg = load_active_config()
    topic, purposes = _resolve_topic_and_purposes(research_args, data_dir, cfg)
    platform = research_args.platform
    raw = f'{DslCommand.RESEARCH} platform:{platform} "{topic}"->{"+".join(purposes)}'
    _log_synthesis_runner_status(cfg)
    packet = asyncio.run(run_research(parse(raw), data_dir, adapter_config=config_extras))
    if _stage_flag(cfg, "synthesis", default=True):
        _attach_synthesis(packet)
    report_path = _write_final_report(
        packet, data_dir, cfg, allow_html=not getattr(args, "no_html", False)
    )
    sys.stdout.write(f"{report_path}\n")
    sys.stdout.flush()
    return 0
