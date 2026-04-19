"""Tests for social_research_probe.stats.regression.run.

Verifies OLS slope and R-squared for perfect linear, flat, and
insufficient-data cases.
"""

import pytest

from social_research_probe.stats.regression import run


def _find(results, name):
    return next((r for r in results if r.name == name), None)


def test_slope_and_r_squared_perfect_linear():
    """A perfect linear sequence should give slope==1 and R-squared==1."""
    data = [0.0, 1.0, 2.0, 3.0, 4.0]
    results = run(data, label="x")
    slope = _find(results, "slope")
    r_sq = _find(results, "r_squared")
    assert slope is not None
    assert r_sq is not None
    assert slope.value == pytest.approx(1.0)
    assert r_sq.value == pytest.approx(1.0)


def test_r_squared_flat_line():
    """A constant series has no variance to explain; R-squared should be 1.0
    by convention (the model predicts all values perfectly as the mean)."""
    data = [5.0, 5.0, 5.0, 5.0]
    results = run(data, label="x")
    r_sq = _find(results, "r_squared")
    assert r_sq is not None
    assert r_sq.value == pytest.approx(1.0)


def test_too_few_points_returns_empty():
    """Fewer than 2 data points cannot produce a regression line."""
    assert run([], label="x") == []
    assert run([7.0], label="x") == []
