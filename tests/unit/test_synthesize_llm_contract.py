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
        items: List of item dicts for items_top5. Defaults to two stub items.

    Returns:
        A dict mimicking the output of synthesize.formatter.build_packet.
    """
    if items is None:
        items = [{"title": "Video A", "scores": {"overall": 0.9}},
                 {"title": "Video B", "scores": {"overall": 0.7}}]
    return {
        "topic": topic,
        "platform": platform,
        "items_top5": items,
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
    """The prompt must embed items_top5 as a JSON fragment.

    We check that the title of a known item appears in the prompt, confirming
    the evidence serialisation ran successfully.
    """
    items = [{"title": "UniqueItemXYZ", "scores": {"overall": 0.8}}]
    packet = _make_packet(items=items)
    prompt = build_synthesis_prompt(packet)
    assert "UniqueItemXYZ" in prompt


def test_build_synthesis_prompt_empty_items():
    """build_synthesis_prompt must not raise even when items_top5 is empty."""
    packet = _make_packet(items=[])
    prompt = build_synthesis_prompt(packet)
    # The JSON for an empty list should appear in the prompt.
    assert "[]" in prompt


# ---------------------------------------------------------------------------
# parse_synthesis_response tests
# ---------------------------------------------------------------------------

def test_parse_synthesis_response_valid():
    """Valid response dict returns both required string fields."""
    raw = {
        "compiled_synthesis": "Interesting trend in AI usage.",
        "opportunity_analysis": "Creators should focus on tutorials.",
    }
    result = parse_synthesis_response(raw)
    assert result["compiled_synthesis"] == "Interesting trend in AI usage."
    assert result["opportunity_analysis"] == "Creators should focus on tutorials."


def test_parse_synthesis_response_missing_key_raises():
    """A response missing 'opportunity_analysis' must raise ValidationError."""
    raw = {"compiled_synthesis": "Some synthesis text."}
    with pytest.raises(ValidationError, match="opportunity_analysis"):
        parse_synthesis_response(raw)


def test_parse_synthesis_response_non_string_raises():
    """A response where a required value is not a string must raise ValidationError."""
    raw = {
        "compiled_synthesis": 42,  # wrong type — should be str
        "opportunity_analysis": "Fine.",
    }
    with pytest.raises(ValidationError, match="compiled_synthesis"):
        parse_synthesis_response(raw)
