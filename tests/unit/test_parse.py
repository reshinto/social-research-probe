"""Deterministic DSL parser. Grammar locked in by tests."""
from __future__ import annotations

import pytest

from social_research_probe.commands.parse import (
    ParsedApplyPending,
    ParsedDiscardPending,
    ParsedRunResearch,
    ParsedUpdatePurposes,
    ParsedUpdateTopics,
    ParseError,
    parse,
)


def test_update_topics_add():
    result = parse('update-topics add:"ai agents"|"robotics"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "add"
    assert result.values == ["ai agents", "robotics"]


def test_update_topics_remove():
    result = parse('update-topics remove:"ai agents"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "remove"
    assert result.values == ["ai agents"]


def test_update_topics_rename():
    result = parse('update-topics rename:"old name"->"new name"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "rename"
    assert result.rename_from == "old name"
    assert result.rename_to == "new name"


def test_update_purposes_add_with_method():
    result = parse('update-purposes add:"trends"="Track emergence across channels"')
    assert isinstance(result, ParsedUpdatePurposes)
    assert result.op == "add"
    assert result.name == "trends"
    assert result.method == "Track emergence across channels"


def test_apply_pending_all():
    result = parse("apply-pending-suggestions topics:all purposes:all")
    assert isinstance(result, ParsedApplyPending)
    assert result.topic_ids == "all"
    assert result.purpose_ids == "all"


def test_apply_pending_ids():
    result = parse("apply-pending-suggestions topics:1,3 purposes:2,4")
    assert isinstance(result, ParsedApplyPending)
    assert result.topic_ids == [1, 3]
    assert result.purpose_ids == [2, 4]


def test_discard_pending():
    result = parse("discard-pending-suggestions topics:2 purposes:all")
    assert isinstance(result, ParsedDiscardPending)
    assert result.topic_ids == [2]
    assert result.purpose_ids == "all"


def test_run_research_single_topic():
    result = parse('run-research platform:youtube "ai agents"->trends')
    assert isinstance(result, ParsedRunResearch)
    assert result.platform == "youtube"
    assert result.topics == [("ai agents", ["trends"])]


def test_run_research_combined_purposes():
    result = parse('run-research platform:youtube "ai agents"->trends+job-opportunities')
    assert isinstance(result, ParsedRunResearch)
    assert result.topics == [("ai agents", ["trends", "job-opportunities"])]


def test_run_research_multiple_topics():
    result = parse('run-research platform:youtube "ai agents"->trends;"robotics"->trends+arbitrage')
    assert isinstance(result, ParsedRunResearch)
    assert result.topics == [
        ("ai agents", ["trends"]),
        ("robotics", ["trends", "arbitrage"]),
    ]


def test_unquoted_topic_raises():
    with pytest.raises(ParseError):
        parse("update-topics add:ai agents")


def test_empty_raises():
    with pytest.raises(ParseError):
        parse("")


def test_unknown_command_raises():
    with pytest.raises(ParseError):
        parse('wobbulate "x"')
