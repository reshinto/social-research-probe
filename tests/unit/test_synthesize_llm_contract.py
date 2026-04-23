"""Unit tests for synthesize/llm_contract.py.

Why this file exists:
    Verifies that build_synthesis_prompt correctly populates the prompt
    template and that parse_synthesis_response enforces the schema contract,
    raising ValidationError on bad input.

Who calls it:
    pytest during CI and local test runs.
"""

from __future__ import annotations

import pytest

from social_research_probe.errors import ValidationError
from social_research_probe.synthesize.llm_contract import (
    build_synthesis_prompt,
    parse_synthesis_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_packet(topic="climate change", platform="youtube", items=None):
    """Return a minimal packet dict for testing build_synthesis_prompt.

    Args:
        topic: Topic string to embed.
        platform: Platform string to embed.
        items: List of item dicts for items_top_n. Defaults to two stub items.

    Returns:
        A dict mimicking the output of synthesize.formatter.build_packet.
    """
    if items is None:
        items = [
            {"title": "Video A", "scores": {"overall": 0.9}},
            {"title": "Video B", "scores": {"overall": 0.7}},
        ]
    return {
        "topic": topic,
        "platform": platform,
        "items_top_n": items,
    }


# ---------------------------------------------------------------------------
# build_synthesis_prompt tests
# ---------------------------------------------------------------------------


def test_build_synthesis_prompt_contains_topic():
    """The formatted prompt must include the packet's topic string."""
    packet = _make_packet(topic="quantum computing")
    prompt = build_synthesis_prompt(packet)
    assert "quantum computing" in prompt


def test_build_synthesis_prompt_contains_platform():
    """The formatted prompt must include the packet's platform string."""
    packet = _make_packet(platform="tiktok")
    prompt = build_synthesis_prompt(packet)
    assert "tiktok" in prompt


def test_build_synthesis_prompt_contains_evidence_json():
    """The prompt must embed items_top_n as a JSON fragment.

    We check that the title of a known item appears in the prompt, confirming
    the evidence serialisation ran successfully.
    """
    items = [{"title": "UniqueItemXYZ", "scores": {"overall": 0.8}}]
    packet = _make_packet(items=items)
    prompt = build_synthesis_prompt(packet)
    assert "UniqueItemXYZ" in prompt


def test_build_synthesis_prompt_empty_items():
    """build_synthesis_prompt must not raise even when items_top_n is empty."""
    packet = _make_packet(items=[])
    prompt = build_synthesis_prompt(packet)
    # The JSON for an empty list should appear in the prompt.
    assert "[]" in prompt


# ---------------------------------------------------------------------------
# parse_synthesis_response tests
# ---------------------------------------------------------------------------


def test_build_synthesis_prompt_contains_synthesis_context_fields():
    """Prompt must surface the structured fields used to ground the final summary."""
    packet = {
        "topic": "ai",
        "platform": "youtube",
        "items_top_n": [
            {
                "title": "T",
                "url": "u",
                "scores": {"trust": 0.5, "trend": 0.5, "opportunity": 0.5, "overall": 0.5},
            }
        ],
        "stats_summary": {
            "highlights": ["trust↔overall r=+0.71"],
            "models_run": [],
            "low_confidence": False,
        },
        "source_validation_summary": {
            "validated": 2,
            "partially": 1,
            "unverified": 0,
            "low_trust": 0,
            "primary": 2,
            "secondary": 1,
            "commentary": 0,
            "notes": "cross-checked",
        },
        "platform_signals_summary": "watch time is rising; comments remain strong",
        "evidence_summary": "multiple creators converge on tutorials",
        "chart_takeaways": ["Overall distribution: n=5"],
        "warnings": ["sparse fetch"],
    }
    prompt = build_synthesis_prompt(packet)
    assert "source_validation_summary" in prompt
    assert "platform_signals_summary" in prompt
    assert "evidence_summary" in prompt
    assert "stats_highlights" in prompt
    assert "chart_takeaways" in prompt
    assert "coverage" in prompt
    assert "warnings" in prompt
    assert "Ground claims" in prompt  # grounding rule


def test_build_synthesis_prompt_tolerates_minimal_packet():
    """A near-empty packet must still produce a renderable prompt."""
    prompt = build_synthesis_prompt({"topic": "x", "platform": "youtube"})
    assert "x" in prompt
    assert "youtube" in prompt


def test_parse_synthesis_response_valid():
    """Valid response dict returns all required string fields."""
    raw = {
        "compiled_synthesis": "Interesting trend in AI usage.",
        "opportunity_analysis": "Creators should focus on tutorials.",
        "report_summary": "Statistics, chart signals, and strategy all point toward tutorials.",
    }
    result = parse_synthesis_response(raw)
    assert result["compiled_synthesis"] == "Interesting trend in AI usage."
    assert result["opportunity_analysis"] == "Creators should focus on tutorials."
    assert (
        result["report_summary"]
        == "Statistics, chart signals, and strategy all point toward tutorials."
    )


def test_parse_synthesis_response_missing_key_raises():
    """A response missing 'report_summary' must raise ValidationError."""
    raw = {
        "compiled_synthesis": "Some synthesis text.",
        "opportunity_analysis": "Some opportunity analysis.",
    }
    with pytest.raises(ValidationError, match="report_summary"):
        parse_synthesis_response(raw)


def test_parse_synthesis_response_missing_opportunity_analysis_raises():
    """A response missing 'opportunity_analysis' must raise ValidationError."""
    raw = {
        "compiled_synthesis": "Some synthesis text.",
        "report_summary": "Some final summary.",
    }
    with pytest.raises(ValidationError, match="opportunity_analysis"):
        parse_synthesis_response(raw)


def test_parse_synthesis_response_non_string_raises():
    """A response where a required value is not a string must raise ValidationError."""
    raw = {
        "compiled_synthesis": 42,  # wrong type — should be str
        "opportunity_analysis": "Fine.",
        "report_summary": "Also fine.",
    }
    with pytest.raises(ValidationError, match="compiled_synthesis"):
        parse_synthesis_response(raw)
