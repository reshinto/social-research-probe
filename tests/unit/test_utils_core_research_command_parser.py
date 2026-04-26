"""Tests for utils.core.research_command_parser."""

from __future__ import annotations

from social_research_probe.utils.core.errors import SrpError
from social_research_probe.utils.core.research_command_parser import (
    ParsedRunResearch,
    ParseError,
    ResearchCommand,
)


def test_research_command_values():
    assert ResearchCommand.UPDATE_TOPICS == "update-topics"
    assert ResearchCommand.RESEARCH == "run-research"
    assert ResearchCommand.SUGGEST_PURPOSES == "suggest-purposes"


def test_parse_error_is_srp_error():
    assert issubclass(ParseError, SrpError)
    assert ParseError.exit_code == 2


def test_parsed_run_research_dataclass():
    parsed = ParsedRunResearch(
        platform="youtube",
        topics=[("ai", ["career"]), ("rust", ["learning", "trends"])],
    )
    assert parsed.platform == "youtube"
    assert parsed.topics[0] == ("ai", ["career"])
    assert parsed.topics[1][1] == ["learning", "trends"]
