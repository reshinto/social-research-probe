"""Tests for social_research_probe.stats.selector.select_and_run.

Verifies the selector applies the correct combination of analyses based
on how many data points are provided.
"""

from social_research_probe.stats.selector import select_and_run


def test_selector_short_data_no_growth():
    """With 2 data points the selector should not include a growth_rate result."""
    results = select_and_run([10.0, 20.0], label="test")
    names = [r.name for r in results]
    assert "growth_rate" not in names
    # Descriptive stats should still be present.
    assert any("mean" in n for n in names)


def test_selector_long_data_includes_growth():
    """With 3+ data points the selector should include a growth_rate result."""
    results = select_and_run([10.0, 20.0, 30.0], label="test")
    names = [r.name for r in results]
    assert "growth_rate" in names


def test_selector_empty_data_returns_empty():
    """Empty input should produce an empty result list."""
    results = select_and_run([], label="test")
    assert results == []
