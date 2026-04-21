"""CLI entry point — thin argparse shell that delegates to command modules."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from social_research_probe.config import load_active_config, resolve_data_dir
from social_research_probe.errors import SrpError, ValidationError
from social_research_probe.llm.registry import get_runner
from social_research_probe.types import RunnerName

from .handlers import (
    _dispatch_config,
    _handle_apply_pending,
    _handle_corroborate_claims,
    _handle_discard_pending,
    _handle_install_skill,
    _handle_render,
    _handle_report,
    _handle_setup,
    _handle_show_pending,
    _handle_show_purposes,
    _handle_show_topics,
    _handle_stage_suggestions,
    _handle_suggest_purposes,
    _handle_suggest_topics,
    _handle_update_purposes,
    _handle_update_topics,
)
from .handlers import (
    _handle_set_secret as _handle_set_secret,
)
from .parsers import _global_parser
from .utils import (
    _emit as _emit,
)
from .utils import (
    _id_selector as _id_selector,
)
from .utils import (
    _to_markdown as _to_markdown,
)
from .utils import (
    _to_text as _to_text,
)


@dataclass(frozen=True)
class _ResearchArgs:
    platform: str
    topic: str  # empty string when query is set
    purposes: tuple[str, ...]  # empty tuple when query is set
    query: str  # empty string when topic/purposes are set


def _parse_simple_research_args(positional: list[str]) -> _ResearchArgs:
    """Parse [platform] topic purposes into a _ResearchArgs.

    If only one non-platform arg is given, treat it as a free-form NL query.
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


def _structured_runner_order(preferred: RunnerName) -> list[RunnerName]:
    """Return preferred structured runner first, then the remaining fallbacks."""
    candidates: list[RunnerName] = ["claude", "gemini", "codex", "local"]
    if preferred == "none":
        return []
    return [preferred, *[name for name in candidates if name != preferred]]


def _run_required_synthesis(packet: dict) -> dict | None:
    """Call structured LLM runners to produce sections 10-11 when enabled.

    Returns a dict with 'compiled_synthesis' and 'opportunity_analysis', or
    None when the runner is disabled or all runner attempts fail.
    """
    from social_research_probe.synthesize.llm_contract import (
        SYNTHESIS_JSON_SCHEMA,
        build_synthesis_prompt,
        parse_synthesis_response,
    )
    from social_research_probe.utils.progress import log

    cfg = load_active_config()
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
        f"[srp] synthesis: all runners failed — sections 10-11 will be omitted. failures=[{detail}]"
    )
    return None


def _attach_synthesis(packet: dict) -> None:
    """Attach synthesized sections 10-11 to a research packet when available."""
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
    """Resolve topic and purposes from either NL query or classic topic/purpose args."""
    from social_research_probe.commands.nl_query import classify_query
    from social_research_probe.utils.progress import log

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
    """Log whether the configured synthesis runner is available."""
    from social_research_probe.utils.progress import log

    preferred = cfg.default_structured_runner
    if preferred == "none":
        log(
            "[srp] synthesis: disabled (llm.runner = 'none'). Set via 'srp config set llm.runner claude|gemini|codex|local'."
        )
    else:
        runner = get_runner(preferred)
        if not runner.health_check():
            log(
                f"[srp] synthesis: runner '{preferred}' binary not found on PATH — sections 10-11 will be skipped. Install the CLI or pick a different runner."
            )


def _handle_research(args: argparse.Namespace, data_dir: Path) -> int:
    """Dispatch research subcommand. Supports classic and NL-query forms."""
    from social_research_probe.commands.parse import parse
    from social_research_probe.pipeline import run_research

    research_args = _parse_simple_research_args(args.args)
    config_extras = {
        "include_shorts": not args.no_shorts,
        "fetch_transcripts": not args.no_transcripts,
    }
    cfg = load_active_config()
    topic, purposes = _resolve_topic_and_purposes(research_args, data_dir, cfg)
    platform = research_args.platform
    raw = f'run-research platform:{platform} "{topic}"->{"+".join(purposes)}'
    _log_synthesis_runner_status(cfg)
    packet = asyncio.run(run_research(parse(raw), data_dir, adapter_config=config_extras))
    if _flag(cfg, "synthesis_enabled", default=True):
        _attach_synthesis(packet)
    report_path = _write_final_report(
        packet, data_dir, cfg, allow_html=not getattr(args, "no_html", False)
    )
    sys.stdout.write(f"{report_path}\n")
    sys.stdout.flush()
    return 0


def _flag(cfg, name: str, *, default: bool) -> bool:
    """Return cfg.feature_enabled(name) if available, else ``default``.

    Lets the CLI accept mock Config objects in tests without forcing every
    fixture to implement the full feature-toggle surface.
    """
    fn = getattr(cfg, "feature_enabled", None)
    if fn is None:
        return default
    try:
        return bool(fn(name))
    except Exception:
        return default


def _write_final_report(packet: dict, data_dir: Path, cfg, *, allow_html: bool) -> str:
    """Always produce a final report file; return its path/URI.

    Honours ``html_report_enabled`` and ``markdown_report_enabled`` feature
    flags as format-selection only — at least one format is always produced
    so stdout never loses the final report path contract, even when every
    other feature is disabled.
    """
    from social_research_probe.render.html import write_html_report
    from social_research_probe.synthesize.formatter import render_full

    html_on = (
        allow_html and _flag(cfg, "html_report_enabled", default=True) and "multi" not in packet
    )
    if html_on:
        try:
            path = write_html_report(packet, data_dir)
            uri = path.resolve().as_uri()
            packet["html_report_path"] = uri
            return uri
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


_HANDLERS = {
    "update-topics": _handle_update_topics,
    "show-topics": _handle_show_topics,
    "update-purposes": _handle_update_purposes,
    "show-purposes": _handle_show_purposes,
    "suggest-topics": _handle_suggest_topics,
    "suggest-purposes": _handle_suggest_purposes,
    "show-pending": _handle_show_pending,
    "apply-pending": _handle_apply_pending,
    "discard-pending": _handle_discard_pending,
    "stage-suggestions": _handle_stage_suggestions,
    "research": _handle_research,
    "corroborate-claims": _handle_corroborate_claims,
    "render": _handle_render,
    "install-skill": _handle_install_skill,
    "setup": _handle_setup,
    "report": _handle_report,
    "config": lambda args, data_dir: _dispatch_config(args, data_dir),
}


def _dispatch(args: argparse.Namespace) -> int:
    """Route parsed args to the appropriate command handler."""
    data_dir = resolve_data_dir(args.data_dir)
    os.environ["SRP_DATA_DIR"] = str(data_dir)
    handler = _HANDLERS.get(args.command)
    if handler is None:
        return 2
    return handler(args, data_dir)


def main(argv: list[str] | None = None) -> int:
    """Parse argv and dispatch to the matching subcommand."""
    import social_research_probe as _srp_pkg

    parser = _global_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        print(f"srp 0.1.0  ({_srp_pkg.__file__})")
        return 0
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return _dispatch(args)
    except SrpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
