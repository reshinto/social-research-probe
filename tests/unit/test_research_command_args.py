"""Tests for CLI research positional argument normalization."""

from __future__ import annotations

import pytest

from social_research_probe.commands.research import _parse_research_input
from social_research_probe.utils.core.errors import ValidationError


def test_explicit_youtube_platform_is_not_treated_as_topic() -> None:
    parsed = _parse_research_input(["youtube", "ai", "latest-news"])

    assert parsed.platform == "youtube"
    assert parsed.topic == "ai"
    assert parsed.purposes == ("latest-news",)
    assert parsed.query == ""


def test_topic_purpose_form_defaults_to_all_platforms() -> None:
    parsed = _parse_research_input(["ai", "latest-news"])

    assert parsed.platform == "all"
    assert parsed.topic == "ai"
    assert parsed.purposes == ("latest-news",)
    assert parsed.query == ""


def test_research_rejects_extra_positional_arguments() -> None:
    with pytest.raises(ValidationError, match="PURPOSES is comma-separated"):
        _parse_research_input(["youtube", "ai", "latest-news", "trends"])
