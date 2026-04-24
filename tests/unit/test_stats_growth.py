"""Tests for social_research_probe.stats.growth.run.

Verifies period-over-period growth rate calculation including increasing,
flat, and insufficient-data cases.
"""

import pytest
from social_research_probe.stats.growth import run


def test_growth_rate_increasing_sequence():
    """Strictly increasing sequence should produce a positive growth rate."""
    results = run([100.0, 200.0, 400.0], label="views")
    assert len(results) == 1
    assert results[0].name == "growth_rate"
    assert results[0].value > 0


def test_growth_rate_flat_sequence():
    """All-equal values should produce a growth rate of exactly 0."""
    results = run([50.0, 50.0, 50.0], label="views")
    assert len(results) == 1
    assert results[0].value == pytest.approx(0.0)


def test_too_few_points_returns_empty():
    """Fewer than 2 data points cannot produce a meaningful growth rate."""
    assert run([], label="views") == []
    assert run([42.0], label="views") == []
