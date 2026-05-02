"""Tests for demo report constants."""

from __future__ import annotations

from social_research_probe.commands import _demo_constants
from social_research_probe.commands._demo_constants import (
    DEMO_DISCLAIMER,
    DEMO_PURPOSE_SET,
    DEMO_THEMES,
    DEMO_TOPIC,
)


def test_topic_marked_synthetic():
    assert DEMO_TOPIC.startswith("[SYNTHETIC DEMO]")


def test_disclaimer_exact_wording():
    assert DEMO_DISCLAIMER == (
        "Synthetic sample data for product demonstration only. Not factual market research."
    )


def test_purpose_set_count():
    assert len(DEMO_PURPOSE_SET) == 3


def test_themes_count_in_range():
    assert 3 <= len(DEMO_THEMES) <= 5


def test_constants_types():
    assert isinstance(DEMO_TOPIC, str)
    assert isinstance(DEMO_DISCLAIMER, str)
    assert isinstance(DEMO_PURPOSE_SET, tuple)
    assert isinstance(DEMO_THEMES, tuple)
    assert all(isinstance(p, str) for p in DEMO_PURPOSE_SET)
    assert all(isinstance(t, str) for t in DEMO_THEMES)


def test_module_exposes_all_constants():
    assert hasattr(_demo_constants, "DEMO_TOPIC")
    assert hasattr(_demo_constants, "DEMO_DISCLAIMER")
    assert hasattr(_demo_constants, "DEMO_PURPOSE_SET")
    assert hasattr(_demo_constants, "DEMO_THEMES")
