"""Research command: run the research pipeline from the CLI."""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from social_research_probe.config import load_active_config
from social_research_probe.services.reporting.writer import write_final_report
from social_research_probe.services.synthesizing.runner import (
    attach_synthesis,
    log_synthesis_runner_status,
)
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.flags import stage_flag


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


def _normalize_to_topic_and_purposes(
    research_args: _ResearchArgs,
    data_dir: Path,
    cfg: object,
) -> tuple[str, tuple[str, ...]]:
    """Ensure research_args has topic and purposes.

    If a natural-language query was provided, classify it into topic and purpose.
    Otherwise, return topic and purposes as-is.
    """
    from social_research_probe.services.llm.nl_query import classify_query
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


def _parse_research_input(positional: list[str]) -> _ResearchArgs:
    """Parse positional CLI arguments into structured research arguments.

    Supports both:
        - Classic form: [platform] topic purposes
        - Natural-language query form: [platform] query

    Platform must be specified and match a registered adapter exactly.
    Use "all" to run on all available platforms.
    """
    from social_research_probe.platforms.registry import REGISTRY

    if len(positional) == 0:
        raise ValidationError(
            "research needs TOPIC and PURPOSES (or a natural-language query)"
        )

    # Check if first positional is a platform or a topic
    first_arg = positional[0]
    if first_arg in REGISTRY:
        platform = first_arg
        rest = positional[1:]
    else:
        # First arg is not a registered platform, default to "all" and treat all args as topic/query
        platform = "all"
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

    research_args = _parse_research_input(args.args)
    config_extras = {
        "include_shorts": not args.no_shorts,
        "fetch_transcripts": not args.no_transcripts,
    }
    cfg = load_active_config()
    topic, purposes = _normalize_to_topic_and_purposes(research_args, data_dir, cfg)
    platform = research_args.platform
    raw = f'{DslCommand.RESEARCH} platform:{platform} "{topic}"->{"+".join(purposes)}'
    log_synthesis_runner_status(cfg)
    packet = asyncio.run(run_research(parse(raw), data_dir, adapter_config=config_extras))
    if stage_flag(cfg, "synthesis", default=True):
        attach_synthesis(packet, cfg)
    report_path = write_final_report(
        packet, data_dir, cfg, allow_html=not getattr(args, "no_html", False)
    )
    sys.stdout.write(f"{report_path}\n")
    sys.stdout.flush()
    return 0
