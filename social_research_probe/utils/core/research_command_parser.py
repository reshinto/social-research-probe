"""Research DSL command models and parsing helpers.

This module defines the small set of command names and parsed data structures
used by the research pipeline's domain-specific language. It also provides
helpers for parsing quoted string fragments used in command payloads.

These helpers are intentionally narrow: they validate simple quoted values and
pipe-delimited quoted lists so downstream research handlers receive predictable,
structured input.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from social_research_probe.utils.core.errors import SrpError


class ResearchCommand(StrEnum):
    """Research DSL command names.

    These values identify actions inside the research pipeline's internal command language.

    They are distinct from top-level CLI command names and are parsed from research workflow
    input.

    Examples:
        Input:
            ResearchCommand
        Output:
            ResearchCommand
    """

    UPDATE_TOPICS = "update-topics"
    SHOW_TOPICS = "show-topics"
    UPDATE_PURPOSES = "update-purposes"
    SHOW_PURPOSES = "show-purposes"
    SUGGEST_TOPICS = "suggest-topics"
    SUGGEST_PURPOSES = "suggest-purposes"
    SHOW_PENDING_SUGGESTIONS = "show-pending-suggestions"
    APPLY_PENDING_SUGGESTIONS = "apply-pending-suggestions"
    DISCARD_PENDING_SUGGESTIONS = "discard-pending-suggestions"
    RESEARCH = "run-research"
    STAGE_SUGGESTIONS = "stage-suggestions"


class ParseError(SrpError):
    """Error raised when research DSL input cannot be parsed.

    The exit code maps parse failures to invalid command usage so callers can report
    malformed input consistently.

    Examples:
        Input:
            ParseError
        Output:
            ParseError
    """

    exit_code = 2


@dataclass(frozen=True)
class ParsedRunResearch:
    """Parsed representation of a run-research command.

    Examples:
        Input:
            ParsedRunResearch
        Output:
            ParsedRunResearch
    """

    platform: str
    topics: list[tuple[str, list[str]]]  # [(topic, [purpose, ...]), ...]
