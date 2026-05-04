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

    Examples:
        Input:
            _ResearchArgs
        Output:
            _ResearchArgs
    """

    platform: str
    topic: str
    purposes: tuple[str, ...]
    query: str


def _classify_query_to_topic_purposes(query: str) -> tuple[str, tuple[str, ...]]:
    """Classify a natural-language query into topic and purpose.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        query: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _classify_query_to_topic_purposes(
                query="AI safety benchmarks",
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    from social_research_probe.services.llm.core.classify_query import classify_query

    classified = classify_query(query)
    return classified.topic, (classified.purpose_name,)


def _normalize_to_topic_and_purposes(
    research_args: _ResearchArgs,
) -> tuple[str, tuple[str, ...]]:
    """Ensure research_args has topic and purposes.

    If a natural-language query was provided, classify it into topic and purpose. Otherwise,
    return topic and purposes as-is.

    Args:
        research_args: Parsed research command arguments before topic and purpose normalization.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _normalize_to_topic_and_purposes(
                research_args="AI safety",
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    if research_args.query:
        return _classify_query_to_topic_purposes(research_args.query)
    return research_args.topic, research_args.purposes


def _parse_research_input(positional: list[str]) -> _ResearchArgs:
    """Parse research input into the project format.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        positional: Positional CLI tokens supplied to the research command.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _parse_research_input(
                positional=["AI safety"],
            )
        Output:
            "AI safety"
    """
    from social_research_probe.platforms import PIPELINES

    if len(positional) == 0:
        raise ValidationError("research needs TOPIC and PURPOSES (or a natural-language query)")

    first_arg = positional[0]
    if first_arg in PIPELINES:
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

    if len(rest) > 2:
        raise ValidationError(
            "research accepts [PLATFORM] TOPIC PURPOSES, where PURPOSES is comma-separated"
        )

    topic, purpose_arg = rest[0], rest[1]
    purposes = tuple(p.strip() for p in purpose_arg.split(",") if p.strip())
    if not purposes:
        raise ValidationError("research needs at least one purpose")
    return _ResearchArgs(platform=platform, topic=topic, purposes=purposes, query="")


def _apply_cli_overrides(args: argparse.Namespace) -> None:
    """Apply CLI flags to platform config overrides.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        args: Parsed argparse namespace for the command being dispatched.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _apply_cli_overrides(
                args=argparse.Namespace(output="json"),
            )
        Output:
            None
    """
    from social_research_probe.config import load_active_config

    load_active_config().apply_platform_overrides(
        {
            "include_shorts": not args.no_shorts,
            "fetch_transcripts": not args.no_transcripts,
            "allow_html": not getattr(args, "no_html", False),
        }
    )


def _execute_research_pipeline(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
    """Build and execute research pipeline, return report.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        platform: Platform name, such as youtube or all, used to select config and pipeline
                  behavior.
        topic: Research topic text or existing topic list used for classification and suggestions.
        purposes: Purpose name or purpose definitions that shape the research goal.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _execute_research_pipeline(
                platform="AI safety",
                topic="AI safety",
                purposes=[{"name": "Opportunity Map"}],
            )
        Output:
            {"enabled": True}
    """
    from social_research_probe.platforms.orchestrator import run_pipeline
    from social_research_probe.utils.core.research_command_parser import ParsedRunResearch

    cmd = ParsedRunResearch(platform=platform, topics=[(topic, list(purposes))])
    return asyncio.run(run_pipeline(cmd))


def run_research_for_watch(
    platform: str,
    topic: str,
    purposes: tuple[str, ...],
    *,
    no_shorts: bool = False,
    no_transcripts: bool = False,
    no_html: bool = False,
) -> dict:
    """Run research for one local watch and return the report."""
    args = argparse.Namespace(
        no_shorts=no_shorts,
        no_transcripts=no_transcripts,
        no_html=no_html,
    )
    _apply_cli_overrides(args)
    return _execute_research_pipeline(platform, topic, purposes)


@log_with_time("[srp] research")
def run(args: argparse.Namespace) -> int:
    """Execute the research pipeline for the 'research' subcommand.

    This is the command boundary: argparse passes raw options in, and the rest of the application
    receives validated project data or a clear error.

    Args:
        args: Parsed argparse namespace for the command being dispatched.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            run(
                args=argparse.Namespace(output="json"),
            )
        Output:
            5
    """
    research_args = _parse_research_input(args.args)
    _apply_cli_overrides(args)
    topic, purposes = _normalize_to_topic_and_purposes(research_args)
    report = _execute_research_pipeline(research_args.platform, topic, purposes)
    report_path = report.get("report_path", "")
    sys.stdout.write(f"{report_path}\n")
    sys.stdout.flush()
    return ExitCode.SUCCESS
