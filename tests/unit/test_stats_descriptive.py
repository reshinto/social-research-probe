"""Tests for social_research_probe.stats.descriptive.run.

Verifies that mean, median, std dev, min, and max are computed correctly
and that edge cases (single point, empty) behave as specified.
"""

import statistics

from social_research_probe.stats.descriptive import run


def _find(results, name_fragment):
    """Return the first StatResult whose name contains name_fragment."""
    return next((r for r in results if name_fragment in r.name), None)


def test_mean_computed_correctly():
    """Mean value should match statistics.mean for the given data."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    results = run(data, label="x")
    mean_result = _find(results, "mean")
    assert mean_result is not None
    assert mean_result.value == statistics.mean(data)


def test_median_computed_correctly():
    """Median value should match statistics.median for the given data."""
    data = [1.0, 2.0, 3.0, 4.0, 100.0]
    results = run(data, label="x")
    median_result = _find(results, "median")
    assert median_result is not None
    assert median_result.value == statistics.median(data)


def test_std_dev_present_for_two_or_more():
    """Std dev should be in the results when there are at least 2 data points."""
    results = run([1.0, 2.0], label="x")
    assert _find(results, "stdev") is not None


def test_min_max_present():
    """Both min and max StatResults should be present for non-empty input."""
    data = [3.0, 1.0, 4.0, 1.0, 5.0]
    results = run(data, label="x")
    min_result = _find(results, "min")
    max_result = _find(results, "max")
    assert min_result is not None
    assert max_result is not None
    assert min_result.value == 1.0
    assert max_result.value == 5.0


def test_empty_input_returns_empty_list():
    """Empty data should produce an empty list, not raise an exception."""
    assert run([], label="x") == []


def test_single_element_no_stdev():
    """Line 62->72: single element skips stdev (len < 2 branch)."""
    results = run([42.0], label="x")
    # Should have mean, median, min, max — but NOT stdev
    assert _find(results, "mean") is not None
    assert _find(results, "stdev") is None
