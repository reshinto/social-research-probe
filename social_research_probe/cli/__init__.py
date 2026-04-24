"""Command-line interface entry point.

Provides an argparse-based shell that parses CLI input and dispatches
execution to subcommand handlers.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from social_research_probe.config import load_active_config, resolve_data_dir
from social_research_probe.utils.core.errors import SrpError, ValidationError
from social_research_probe.llm.registry import get_runner
from social_research_probe.utils.core.types import RunnerName

from .handlers import (
    _dispatch_config,
    _handle_apply_pending,
    _handle_corroborate_claims,
    _handle_discard_pending,
    _handle_install_skill,
    _handle_render,
    _handle_report,
    _handle_serve_report,
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
from .utils import _emit as _emit
from .utils import _id_selector as _id_selector
from .utils import _to_markdown as _to_markdown
from .utils import _to_text as _to_text


@dataclass(frozen=True)
class _ResearchArgs:
    """Container for normalized research arguments.

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


def _parse_simple_research_args(positional: list[str]) -> _ResearchArgs:
    """Parse positional CLI arguments into structured research arguments.

    Supports both:
        - Classic form: [platform] topic purposes
        - Natural-language query form: [platform] query

    Args:
        positional: Raw positional CLI arguments.

    Returns:
        Normalized research arguments.

    Raises:
        ValidationError: If required arguments are missing or invalid.
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
    """Return an ordered list of structured runners.

    The preferred runner is placed first, followed by remaining candidates
    in fallback order.

    Args:
        preferred: Preferred runner.

    Returns:
        Ordered list of runner names.
    """
    candidates: list[RunnerName] = ["claude", "gemini", "codex", "local"]
    if preferred == "none":
        return []
    return [preferred, *[name for name in candidates if name != preferred]]


def _run_required_synthesis(packet: dict) -> dict | None:
    """Run the synthesis pipeline using structured LLM runners.

    Attempts multiple runners in fallback order until one succeeds.

    Args:
        packet: Input research packet.

    Returns:
        A dictionary containing synthesis fields if successful, otherwise None.
    """
    from social_research_probe.synthesize.llm_contract import (
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
    """Attach synthesis results to a research packet in place.

    Args:
        packet: Research packet to update.
    """
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
    """Resolve topic and purposes from structured input or a query.

    Args:
        research_args: Parsed research arguments.
        data_dir: Data directory.
        cfg: Active configuration.

    Returns:
        Resolved topic and purposes.
    """
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
    """Log synthesis runner availability based on configuration.

    Args:
        cfg: Active configuration.
    """
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


def _handle_research(args: argparse.Namespace, data_dir: Path) -> int:
    """Execute the research pipeline for the 'research' subcommand.

    Args:
        args: Parsed CLI arguments.
        data_dir: Data directory.

    Returns:
        Exit status code.
    """
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
    if _stage_flag(cfg, "synthesis", default=True):
        _attach_synthesis(packet)
    report_path = _write_final_report(
        packet, data_dir, cfg, allow_html=not getattr(args, "no_html", False)
    )
    sys.stdout.write(f"{report_path}\n")
    sys.stdout.flush()
    return 0


def _stage_flag(cfg, name: str, *, default: bool) -> bool:
    """Check whether a pipeline stage is enabled.

    Args:
        cfg: Configuration object.
        name: Stage name.
        default: Fallback value if lookup fails.

    Returns:
        True if the stage is enabled, otherwise the fallback value.
    """
    fn = getattr(cfg, "stage_enabled", None)
    if fn is None:
        return default
    try:
        return bool(fn(name))
    except Exception:
        return default


def _service_flag(cfg, name: str, *, default: bool) -> bool:
    """Check whether a service is enabled.

    Args:
        cfg: Configuration object.
        name: Service name.
        default: Fallback value if lookup fails.

    Returns:
        True if the service is enabled, otherwise the fallback value.
    """
    fn = getattr(cfg, "service_enabled", None)
    if fn is None:
        return default
    try:
        return bool(fn(name))
    except Exception:
        return default


def _write_final_report(packet: dict, data_dir: Path, cfg, *, allow_html: bool) -> str:
    """Write the final report and return an access path or command.

    Always produces a report file. Markdown output is used as a fallback
    when HTML generation is disabled or fails, ensuring a consistent
    output contract.

    Args:
        packet: Research output packet.
        data_dir: Data directory.
        cfg: Active configuration.
        allow_html: Whether HTML output is allowed.

    Returns:
        File path or command to access the report.
    """
    from social_research_probe.synthesize.formatter import render_full
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
    "serve-report": _handle_serve_report,
    "config": lambda args, data_dir: _dispatch_config(args, data_dir),
}


def _dispatch(args: argparse.Namespace) -> int:
    """Dispatch parsed CLI arguments to the appropriate handler.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code from the selected handler.
    """
    data_dir = resolve_data_dir(args.data_dir)
    os.environ["SRP_DATA_DIR"] = str(data_dir)
    handler = _HANDLERS.get(args.command)
    if handler is None:
        return 2
    return handler(args, data_dir)


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Parses arguments and dispatches execution to subcommand handlers.

    Args:
        argv: Optional argument list. Defaults to sys.argv.

    Returns:
        Exit status code.

    Raises:
        SrpError: Raised by handlers and converted to exit codes.
    """
    import social_research_probe as _srp_pkg

    parser = _global_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        print(f"srp {_srp_pkg.get_version()}  ({_srp_pkg.__file__})")
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
