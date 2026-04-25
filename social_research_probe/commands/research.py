"""Research command: run the research pipeline from the CLI."""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.exit_codes import ExitCode
from social_research_probe.utils.display.progress import log_with_time


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


def _classify_query_to_topic_purposes(query: str) -> tuple[str, tuple[str, ...]]:
    """Classify a natural-language query into topic and purpose."""
    from social_research_probe.services.llm.classify_query import classify_query

    classified = classify_query(query)
    return classified.topic, (classified.purpose_name,)


def _normalize_to_topic_and_purposes(
    research_args: _ResearchArgs,
) -> tuple[str, tuple[str, ...]]:
    """Ensure research_args has topic and purposes.

    If a natural-language query was provided, classify it into topic and purpose.
    Otherwise, return topic and purposes as-is.
    """
    if research_args.query:
        return _classify_query_to_topic_purposes(research_args.query)
    return research_args.topic, research_args.purposes


def _parse_research_input(positional: list[str]) -> _ResearchArgs:
    """Parse positional CLI arguments into structured research arguments.

    Current behavior:
        - If the first positional argument matches a registered platform,
        it is used as the platform.
        - If the first positional argument does not match a registered platform,
        the platform defaults to "all".
        - If one argument remains after platform detection, it is treated as a
        natural-language query.
        - If two or more arguments remain after platform detection, the first is
        treated as the topic and the second is treated as the comma-separated
        purposes.

    Important limitations:
        - Extra arguments after topic and purposes are silently ignored.
        - Unknown platform-looking values are not rejected; they are treated as
        topics unless they match CLIENTS.
        - The default platform is hard-coded as "all".

    Examples:
        ["youtube", "quant", "job-opportunity"]
            -> platform="youtube", topic="quant", purposes=("job-opportunity",)

        ["youtube", "what are the job opportunities for quants"]
            -> platform="youtube", query="what are the job opportunities for quants"

        ["quant", "job-opportunity"]
            -> platform="all", topic="quant", purposes=("job-opportunity",)

        ["wrongPlatformName", "quant", "job-opportunity"]
            -> platform="all", topic="wrongPlatformName", purposes=("quant",)
            and "job-opportunity" is ignored
    """
    from social_research_probe.platforms.registry import CLIENTS

    if len(positional) == 0:
        raise ValidationError(
            "research needs TOPIC and PURPOSES (or a natural-language query)"
        )

    first_arg = positional[0]
    if first_arg in CLIENTS:
        platform = first_arg
        rest = positional[1:]
    else:
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


def _apply_cli_overrides(args: argparse.Namespace) -> None:
    """Apply CLI flags to platform config overrides."""
    from social_research_probe.config import load_active_config

    load_active_config().apply_platform_overrides(
        {
            "include_shorts": not args.no_shorts,
            "fetch_transcripts": not args.no_transcripts,
            "allow_html": not getattr(args, "no_html", False),
        }
    )


def _execute_research_pipeline(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
    """Build and execute research pipeline, return packet."""
    from social_research_probe.utils.core.research_command_parser import ParsedRunResearch
    from social_research_probe.platforms.orchestrator import run_pipeline

    cmd = ParsedRunResearch(platform=platform, topics=[(topic, list(purposes))])
    return asyncio.run(run_pipeline(cmd))


@log_with_time("[srp] research: platform={research_args.platform}")
def run(args: argparse.Namespace) -> int:
    """Execute the research pipeline for the 'research' subcommand."""
    research_args = _parse_research_input(args.args)
    _apply_cli_overrides(args)
    topic, purposes = _normalize_to_topic_and_purposes(research_args)
    packet = _execute_research_pipeline(research_args.platform, topic, purposes)
    report_path = packet.get("report_path", "")
    sys.stdout.write(f"{report_path}\n")
    sys.stdout.flush()
    return ExitCode.SUCCESS
