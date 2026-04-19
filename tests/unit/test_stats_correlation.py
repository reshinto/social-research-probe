"""Tests for social_research_probe.stats.correlation.run.

Verifies Pearson r for perfect positive, perfect negative, unequal-length,
and insufficient-data cases.
"""

import pytest

from social_research_probe.stats.correlation import run


def test_perfect_positive_correlation():
    """Identical series should give Pearson r == 1.0."""
    series = [1.0, 2.0, 3.0, 4.0, 5.0]
    results = run(series, series, label_a="a", label_b="b")
    assert len(results) == 1
    assert results[0].name == "pearson_r"
    assert results[0].value == pytest.approx(1.0)


def test_perfect_negative_correlation():
    """A series paired with its negation should give Pearson r == -1.0."""
    series_a = [1.0, 2.0, 3.0, 4.0, 5.0]
    series_b = [-1.0, -2.0, -3.0, -4.0, -5.0]
    results = run(series_a, series_b, label_a="a", label_b="b")
    assert len(results) == 1
    assert results[0].value == pytest.approx(-1.0)


def test_unequal_length_returns_empty():
    """Series of different lengths should return an empty list."""
    assert run([1.0, 2.0], [1.0, 2.0, 3.0]) == []


def test_too_few_points_returns_empty():
    """Fewer than 2 data points cannot produce a meaningful correlation."""
    assert run([], []) == []
    assert run([1.0], [1.0]) == []


def test_zero_variance_returns_empty():
    """Line 57: constant series has zero variance; correlation is undefined → []."""
    # Both series have zero variance (all values identical)
    result = run([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])
    assert result == []
