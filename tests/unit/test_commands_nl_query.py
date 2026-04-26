"""Unit tests for commands/nl_query.py and llm/schemas.py.

Covers classify_query end-to-end using a stub LLMRunner so no real subprocess
is needed. Also verifies the JSON schema constant structure.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from social_research_probe.errors import ValidationError
from social_research_probe.llm.schemas import NL_QUERY_CLASSIFICATION_SCHEMA

from social_research_probe.services.llm.classify_query import (
    _RUNNER_CANDIDATES,
    ClassifiedQuery,
    _build_classification_prompt,
    _is_valid_result,
    classify_query,
)
from social_research_probe.services.llm.runners import prioritize_runner
from social_research_probe.utils.core.strings import normalize_whitespace

# ---------------------------------------------------------------------------
# NL_QUERY_CLASSIFICATION_SCHEMA
# ---------------------------------------------------------------------------


def test_schema_has_required_keys() -> None:
    """Schema declares all three fields as required."""
    assert set(NL_QUERY_CLASSIFICATION_SCHEMA["required"]) == {
        "topic",
        "purpose_name",
        "purpose_method",
    }


def test_schema_no_additional_properties() -> None:
    """Schema disallows extra keys."""
    assert NL_QUERY_CLASSIFICATION_SCHEMA["additionalProperties"] is False


def test_schema_field_types() -> None:
    """All three fields are declared as strings with length constraints."""
    props = NL_QUERY_CLASSIFICATION_SCHEMA["properties"]
    for key in ("topic", "purpose_name", "purpose_method"):
        assert props[key]["type"] == "string"
        assert props[key]["minLength"] == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_normalize_strips_and_lowercases() -> None:
    """normalize_whitespace strips whitespace and lowercases the value."""
    assert normalize_whitespace("  Hello World  ") == "hello world"


def test_normalize_collapses_multiple_spaces() -> None:
    """normalize_whitespace collapses runs of spaces to a single space."""
    assert normalize_whitespace("hello   world") == "hello world"


def test_is_valid_result_true_for_complete_dict() -> None:
    """_is_valid_result returns True when all three keys have non-empty strings."""
    result = {"topic": "ai", "purpose_name": "news", "purpose_method": "latest updates"}
    assert _is_valid_result(result) is True


def test_is_valid_result_false_when_key_missing() -> None:
    """_is_valid_result returns False when a required key is absent."""
    assert _is_valid_result({"topic": "ai", "purpose_name": "news"}) is False


def test_is_valid_result_false_when_value_empty() -> None:
    """_is_valid_result returns False when a value is an empty string."""
    result = {"topic": "", "purpose_name": "news", "purpose_method": "updates"}
    assert _is_valid_result(result) is False


def test_is_valid_result_false_when_value_whitespace_only() -> None:
    """_is_valid_result returns False when a value is only whitespace."""
    result = {"topic": "  ", "purpose_name": "news", "purpose_method": "updates"}
    assert _is_valid_result(result) is False


def test_is_valid_result_false_when_value_not_string() -> None:
    """_is_valid_result returns False when a value is not a string."""
    result = {"topic": 42, "purpose_name": "news", "purpose_method": "updates"}
    assert _is_valid_result(result) is False


def test_runner_order_puts_preferred_first() -> None:
    """prioritize_runner places the preferred runner at index 0."""
    order = prioritize_runner(_RUNNER_CANDIDATES, "gemini")
    assert order[0] == "gemini"
    assert "claude" in order
    assert order.count("gemini") == 1


def test_runner_order_no_duplicates() -> None:
    """prioritize_runner never repeats a name."""
    order = prioritize_runner(_RUNNER_CANDIDATES, "claude")
    assert len(order) == len(set(order))


# ---------------------------------------------------------------------------
# _build_classification_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_includes_query() -> None:
    """Prompt body contains the raw query string."""
    prompt = _build_classification_prompt("find AI jobs", [], [])
    assert "find AI jobs" in prompt


def test_build_prompt_shows_none_yet_when_empty() -> None:
    """Prompt shows '(none yet)' when existing lists are empty."""
    prompt = _build_classification_prompt("q", [], [])
    assert "(none yet)" in prompt


def test_build_prompt_includes_existing_topics() -> None:
    """Prompt includes existing topic names when provided."""
    prompt = _build_classification_prompt("q", ["ai", "robotics"], [])
    assert "ai" in prompt
    assert "robotics" in prompt


def test_build_prompt_includes_existing_purposes() -> None:
    """Prompt includes existing purpose names when provided."""
    prompt = _build_classification_prompt("q", [], ["latest-news", "deep-dive"])
    assert "latest-news" in prompt
    assert "deep-dive" in prompt


# ---------------------------------------------------------------------------
# classify_query — Config stubs and runner mocks
# ---------------------------------------------------------------------------


def _make_cfg(runner_name: str = "claude") -> MagicMock:
    """Build a minimal Config stub with the given default_structured_runner."""
    cfg = MagicMock()
    cfg.default_structured_runner = runner_name
    cfg.service_enabled.side_effect = lambda name: True
    return cfg


def _make_runner(
    *,
    healthy: bool = True,
    result: dict | None = None,
    raises: Exception | None = None,
) -> MagicMock:
    """Build a stub LLMRunner with controllable health_check and run behaviour."""
    runner = MagicMock()
    runner.health_check.return_value = healthy
    if raises is not None:
        runner.run.side_effect = raises
    else:
        runner.run.return_value = result or {
            "topic": "ai",
            "purpose_name": "latest-news",
            "purpose_method": "latest news and updates",
        }
    return runner


def test_classify_query_raises_when_runner_disabled(tmp_data_dir: Path) -> None:
    """classify_query raises ValidationError when runner is 'none'."""
    _make_cfg("none")
    with pytest.raises(ValidationError, match=r"llm\.runner is disabled"):
        classify_query("find AI jobs")


def test_classify_query_raises_when_llm_service_disabled(tmp_data_dir: Path) -> None:
    cfg = _make_cfg("claude")
    cfg.service_enabled.side_effect = lambda name: name != "llm"
    with pytest.raises(ValidationError, match=r"services\.llm is false"):
        classify_query("find AI jobs")


def test_classify_query_returns_classified_query(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_query returns a ClassifiedQuery with correct normalized fields."""
    _make_cfg("claude")
    runner = _make_runner(
        result={
            "topic": "  AI  ",
            "purpose_name": " Latest-News ",
            "purpose_method": " Latest News And Updates ",
        }
    )
    monkeypatch.setattr("social_research_probe.commands.nl_query.get_runner", lambda name: runner)
    result = classify_query("find AI jobs")
    assert isinstance(result, ClassifiedQuery)
    assert result.topic == "ai"
    assert result.purpose_name == "latest-news"
    assert result.purpose_method == "latest news and updates"
    assert result.topic_created is True
    assert result.purpose_created is True


def test_classify_query_topic_already_exists(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """topic_created is False when the topic already exists (DuplicateError)."""
    from social_research_probe.commands import add_topics

    add_topics(tmp_data_dir, ["ai"], force=False)

    _make_cfg("claude")
    runner = _make_runner()
    monkeypatch.setattr("social_research_probe.commands.nl_query.get_runner", lambda name: runner)
    result = classify_query("find AI jobs")
    assert result.topic_created is False
    assert result.purpose_created is True


def test_classify_query_purpose_already_exists(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """purpose_created is False when the purpose already exists (DuplicateError)."""
    from social_research_probe.commands import add_purpose

    add_purpose(tmp_data_dir, name="latest-news", method="latest news and updates", force=False)

    _make_cfg("claude")
    runner = _make_runner()
    monkeypatch.setattr("social_research_probe.commands.nl_query.get_runner", lambda name: runner)
    result = classify_query("find AI jobs")
    assert result.topic_created is True
    assert result.purpose_created is False


def test_classify_query_skips_unhealthy_runner(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_query skips runners whose health_check returns False."""
    _make_cfg("claude")
    unhealthy = _make_runner(healthy=False)
    healthy = _make_runner(healthy=True)

    call_order: list[str] = []

    def fake_get_runner(name: str):
        call_order.append(name)
        # First call (claude) is unhealthy; second (gemini onward) is healthy.
        if len(call_order) == 1:
            return unhealthy
        return healthy

    monkeypatch.setattr("social_research_probe.commands.nl_query.get_runner", fake_get_runner)
    result = classify_query("q")
    assert result.topic == "ai"
    # unhealthy runner's run() must never have been called
    unhealthy.run.assert_not_called()


def test_classify_query_skips_runner_that_raises(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_query moves on when a runner.run() raises an exception."""
    _make_cfg("claude")
    failing = _make_runner(raises=RuntimeError("boom"))
    good = _make_runner()

    runners = {"claude": failing, "gemini": good}
    monkeypatch.setattr(
        "social_research_probe.commands.nl_query.get_runner",
        lambda name: runners.get(name, good),
    )
    result = classify_query("q")
    assert result.topic == "ai"


def test_classify_query_skips_invalid_result(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_query skips a runner whose result fails validation."""
    _make_cfg("claude")
    bad = _make_runner(result={"topic": "", "purpose_name": "x", "purpose_method": "y"})
    good = _make_runner()

    runners = {"claude": bad, "gemini": good}
    monkeypatch.setattr(
        "social_research_probe.commands.nl_query.get_runner",
        lambda name: runners.get(name, good),
    )
    result = classify_query("q")
    assert result.topic == "ai"


def test_classify_query_raises_when_all_runners_fail(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_query raises ValidationError when every runner fails."""
    _make_cfg("claude")
    broken = _make_runner(raises=RuntimeError("always fails"))
    monkeypatch.setattr("social_research_probe.commands.nl_query.get_runner", lambda name: broken)
    with pytest.raises(ValidationError, match="all LLM runners failed"):
        classify_query("q")


def test_classify_query_propagates_unexpected_topic_error(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_query re-raises non-DuplicateError from add_topics."""
    _make_cfg("claude")
    runner = _make_runner()
    monkeypatch.setattr("social_research_probe.commands.nl_query.get_runner", lambda name: runner)
    monkeypatch.setattr(
        "social_research_probe.commands.nl_query.add_topics",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(OSError, match="disk full"):
        classify_query("q")


def test_classify_query_propagates_unexpected_purpose_error(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_query re-raises non-DuplicateError from add_purpose."""
    _make_cfg("claude")
    runner = _make_runner()
    monkeypatch.setattr("social_research_probe.commands.nl_query.get_runner", lambda name: runner)
    monkeypatch.setattr(
        "social_research_probe.commands.nl_query.add_purpose",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(OSError, match="disk full"):
        classify_query("q")
