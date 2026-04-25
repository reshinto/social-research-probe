"""Deterministic DSL parser. Grammar locked in by tests."""

from __future__ import annotations

import pytest

from social_research_probe.utils.core.research_command_parser import (
    ResearchCommand,
    ParsedApplyPending,
    ParsedDiscardPending,
    ParsedRunResearch,
    ParsedUpdatePurposes,
    ParsedUpdateTopics,
    ParseError,
    parse,
)


def test_update_topics_add():
    result = parse(f'{ResearchCommand.UPDATE_TOPICS} add:"ai agents"|"robotics"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "add"
    assert result.values == ["ai agents", "robotics"]


def test_update_topics_remove():
    result = parse(f'{ResearchCommand.UPDATE_TOPICS} remove:"ai agents"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "remove"
    assert result.values == ["ai agents"]


def test_update_topics_rename():
    result = parse(f'{ResearchCommand.UPDATE_TOPICS} rename:"old name"->"new name"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "rename"
    assert result.rename_from == "old name"
    assert result.rename_to == "new name"


def test_update_purposes_add_with_method():
    result = parse(f'{ResearchCommand.UPDATE_PURPOSES} add:"trends"="Track emergence across channels"')
    assert isinstance(result, ParsedUpdatePurposes)
    assert result.op == "add"
    assert result.name == "trends"
    assert result.method == "Track emergence across channels"


def test_apply_pending_all():
    result = parse(f"{ResearchCommand.APPLY_PENDING_SUGGESTIONS} topics:all purposes:all")
    assert isinstance(result, ParsedApplyPending)
    assert result.topic_ids == "all"
    assert result.purpose_ids == "all"


def test_apply_pending_ids():
    result = parse(f"{ResearchCommand.APPLY_PENDING_SUGGESTIONS} topics:1,3 purposes:2,4")
    assert isinstance(result, ParsedApplyPending)
    assert result.topic_ids == [1, 3]
    assert result.purpose_ids == [2, 4]


def test_discard_pending():
    result = parse(f"{ResearchCommand.DISCARD_PENDING_SUGGESTIONS} topics:2 purposes:all")
    assert isinstance(result, ParsedDiscardPending)
    assert result.topic_ids == [2]
    assert result.purpose_ids == "all"


def test_run_research_single_topic():
    result = parse(f'{ResearchCommand.RESEARCH} platform:youtube "ai agents"->trends')
    assert isinstance(result, ParsedRunResearch)
    assert result.platform == "youtube"
    assert result.topics == [("ai agents", ["trends"])]


def test_run_research_combined_purposes():
    result = parse(f'{ResearchCommand.RESEARCH} platform:youtube "ai agents"->trends+job-opportunities')
    assert isinstance(result, ParsedRunResearch)
    assert result.topics == [("ai agents", ["trends", "job-opportunities"])]


def test_run_research_multiple_topics():
    result = parse(
        f'{ResearchCommand.RESEARCH} platform:youtube "ai agents"->trends;"robotics"->trends+arbitrage'
    )
    assert isinstance(result, ParsedRunResearch)
    assert result.topics == [
        ("ai agents", ["trends"]),
        ("robotics", ["trends", "arbitrage"]),
    ]


def test_unquoted_topic_raises():
    with pytest.raises(ParseError):
        parse(f"{ResearchCommand.UPDATE_TOPICS} add:ai agents")


def test_empty_raises():
    with pytest.raises(ParseError):
        parse("")


def test_unknown_command_raises():
    with pytest.raises(ParseError):
        parse('wobbulate "x"')


def test_rename_trailing_garbage_raises():
    with pytest.raises(ParseError, match="unexpected trailing content"):
        parse(f'{ResearchCommand.UPDATE_TOPICS} rename:"old"->"new"GARBAGE')


def test_add_purpose_trailing_garbage_raises():
    with pytest.raises(ParseError, match="unexpected trailing content"):
        parse(f'{ResearchCommand.UPDATE_PURPOSES} add:"trends"="method"GARBAGE')


# --- Additional parse coverage ---


def test_unterminated_quoted_string_raises():
    # take_quoted: missing closing quote (line 98)
    with pytest.raises(ParseError, match="unterminated"):
        parse(f'{ResearchCommand.UPDATE_TOPICS} add:"unclosed')


def test_quoted_list_unexpected_separator_raises():
    # parse_quoted_list: separator other than '|' (line 111)
    with pytest.raises(ParseError):
        parse(f'{ResearchCommand.UPDATE_TOPICS} add:"a","b"')


def test_id_selector_all():
    # parse_id_selector returns "all" (line 117-118)
    from social_research_probe.utils.core.research_command_parser import parse_id_selector

    assert parse_id_selector("all") == "all"


def test_id_selector_invalid_raises():
    # parse_id_selector with non-integer raises ParseError (lines 121-122)
    from social_research_probe.utils.core.research_command_parser import parse_id_selector

    with pytest.raises(ParseError):
        parse_id_selector("abc")


def test_update_topics_invalid_op_raises():
    # _parse_update_topics: unrecognised prefix (line 161 / 166)
    with pytest.raises(ParseError):
        parse(f'{ResearchCommand.UPDATE_TOPICS} mutate:"x"')


def test_update_purposes_remove():
    # _parse_update_purposes remove branch (lines 179-180)
    result = parse(f'{ResearchCommand.UPDATE_PURPOSES} remove:"old-purpose"')
    from social_research_probe.utils.core.research_command_parser import ParsedUpdatePurposes

    assert isinstance(result, ParsedUpdatePurposes)
    assert result.op == "remove"
    assert result.values == ["old-purpose"]


def test_update_purposes_rename():
    # _parse_update_purposes rename branch (lines 181-189)
    result = parse(f'{ResearchCommand.UPDATE_PURPOSES} rename:"old"->"new"')
    from social_research_probe.utils.core.research_command_parser import ParsedUpdatePurposes

    assert isinstance(result, ParsedUpdatePurposes)
    assert result.op == "rename"
    assert result.rename_from == "old"
    assert result.rename_to == "new"


def test_update_purposes_rename_trailing_garbage_raises():
    # _parse_update_purposes rename trailing content (line 188)
    with pytest.raises(ParseError, match="unexpected trailing content"):
        parse(f'{ResearchCommand.UPDATE_PURPOSES} rename:"old"->"new"JUNK')


def test_update_purposes_bad_op_raises():
    # _parse_update_purposes: unrecognised prefix (line 190)
    with pytest.raises(ParseError):
        parse(f'{ResearchCommand.UPDATE_PURPOSES} mutate:"x"')


def test_update_purposes_add_missing_eq_raises():
    # _parse_update_purposes add: '=' not found (line 174)
    with pytest.raises(ParseError):
        parse(f'{ResearchCommand.UPDATE_PURPOSES} add:"name"X"method"')


def test_pending_selectors_unexpected_token_raises():
    # _parse_pending_selectors: token with no ':' and nothing before it (line 213)
    with pytest.raises(ParseError):
        parse(f"{ResearchCommand.APPLY_PENDING_SUGGESTIONS} badtoken")


def test_pending_selectors_missing_topics_raises():
    # _parse_pending_selectors: 'purposes' present but 'topics' missing
    with pytest.raises(ParseError, match="requires topics:"):
        parse(f"{ResearchCommand.APPLY_PENDING_SUGGESTIONS} purposes:all")


def test_pending_selectors_missing_both_raises():
    # _parse_pending_selectors: neither topics nor purposes
    with pytest.raises(ParseError):
        parse(f"{ResearchCommand.APPLY_PENDING_SUGGESTIONS} x:1 y:2")


def testkv_pair_no_value_raises():
    # kv_pair: chunk like "key:" with empty value (line 223)
    from social_research_probe.utils.core.research_command_parser import kv_pair

    with pytest.raises(ParseError):
        kv_pair("key:")


def test_run_research_no_platform_raises():
    # _parse_run_research: doesn't start with 'platform:' (line 229)
    with pytest.raises(ParseError, match="platform:NAME"):
        parse(f'{ResearchCommand.RESEARCH} "AI"->trends')


def test_run_research_empty_platform_raises():
    # _parse_run_research: platform name or topic section empty (line 233)
    with pytest.raises(ParseError):
        parse(f"{ResearchCommand.RESEARCH} platform:")


def test_run_research_missing_arrow_raises():
    # _parse_run_research: missing '->' after topic (line 242)
    with pytest.raises(ParseError):
        parse(f'{ResearchCommand.RESEARCH} platform:youtube "AI"::trends')


def test_run_research_no_purposes_raises():
    # _parse_run_research: empty purposes after '->' (line 245)
    with pytest.raises(ParseError, match="no purposes"):
        parse(f'{ResearchCommand.RESEARCH} platform:youtube "AI"->')


def test_run_research_invalid_purpose_name_raises():
    # _parse_run_research: purpose with spaces/special chars (lines 247-249)
    with pytest.raises(ParseError, match="invalid purpose name"):
        parse(f'{ResearchCommand.RESEARCH} platform:youtube "AI"->has spaces')


def test_run_research_no_topics_raises():
    # _parse_run_research: only empty entries after splitting by ';' (line 253)
    with pytest.raises(ParseError, match="at least one topic"):
        parse(f"{ResearchCommand.RESEARCH} platform:youtube ;")


def test_update_topics_rename_missing_arrow_raises():
    """Line 161: _parse_update_topics rename missing '->' raises ParseError."""
    with pytest.raises(ParseError, match="expected '->'"):
        parse(f'{ResearchCommand.UPDATE_TOPICS} rename:"old""new"')


def test_update_purposes_rename_missing_arrow_raises():
    """Line 185: _parse_update_purposes rename missing '->' raises ParseError."""
    with pytest.raises(ParseError, match="expected '->'"):
        parse(f'{ResearchCommand.UPDATE_PURPOSES} rename:"old""new"')


def test_pending_selectors_space_in_id_list():
    """Line 211: _parse_pending_selectors merges tokens without ':' into previous."""
    # "topics:1, 2" splits into ["topics:1,", "2"] — the "2" has no ':' and merged is non-empty
    # so merged[-1] += "2" giving "topics:1,2"
    result = parse(f"{ResearchCommand.APPLY_PENDING_SUGGESTIONS} topics:1, 2 purposes:all")
    assert isinstance(result, ParsedApplyPending)
    assert result.topic_ids == [1, 2]
