"""Tests for social_research_probe.stats.outliers.run.

Verifies z-score outlier detection with a spike, a flat series, and
insufficient-data cases.
"""

import pytest

from social_research_probe.stats.outliers import run


def _find(results, name):
    return next((r for r in results if r.name == name), None)


def test_outlier_detection_with_spike():
    """A large spike should be identified as an outlier."""
    # Values 1-5 are clustered; 1000 is a clear spike.
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 1000.0]
    results = run(data, label="x", threshold=2.0)
    outlier_count = _find(results, "outlier_count")
    assert outlier_count is not None
    assert outlier_count.value >= 1


def test_no_outliers_flat_series():
    """A series with no variation should report zero outliers (std dev==0 guard)."""
    data = [5.0, 5.0, 5.0, 5.0, 5.0]
    results = run(data, label="x", threshold=2.0)
    outlier_count = _find(results, "outlier_count")
    assert outlier_count is not None
    assert outlier_count.value == pytest.approx(0.0)


def test_too_few_points_returns_empty():
    """Fewer than 2 data points cannot support z-score calculation."""
    assert run([], label="x") == []
    assert run([42.0], label="x") == []
