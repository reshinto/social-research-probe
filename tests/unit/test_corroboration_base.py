"""Tests for corroboration/base.py — CorroborationResult and CorroborationBackend.

What: Verifies the dataclass defaults and that the ABC cannot be instantiated.
Who calls it: pytest, as part of the unit test suite.
"""

from __future__ import annotations

import pytest

from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult


def test_corroboration_result_defaults():
    """sources and backend_name default to empty list and empty string respectively."""
    result = CorroborationResult(
        verdict="supported",
        confidence=0.8,
        reasoning="Test reasoning.",
    )
    assert result.sources == []
    assert result.backend_name == ""
    # Check that the provided fields are stored correctly.
    assert result.verdict == "supported"
    assert result.confidence == 0.8
    assert result.reasoning == "Test reasoning."


def test_corroboration_backend_is_abstract():
    """CorroborationBackend cannot be instantiated directly — it is an ABC."""
    with pytest.raises(TypeError):
        CorroborationBackend()
