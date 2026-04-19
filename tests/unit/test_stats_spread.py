"""Tests for social_research_probe.stats.spread.run.

Verifies IQR and range computation and the minimum-data-point guard.
"""

from social_research_probe.stats.spread import run


def _find(results, name):
    return next((r for r in results if r.name == name), None)


def test_iqr_and_range_present():
    """IQR and range should both be present for a dataset with 4+ points."""
    data = [1.0, 2.0, 8.0, 9.0, 10.0, 100.0]
    results = run(data, label="x")
    assert _find(results, "iqr") is not None
    assert _find(results, "range") is not None
    # Range must equal max - min.
    assert _find(results, "range").value == max(data) - min(data)


def test_too_few_points_returns_empty():
    """Fewer than 4 data points cannot produce quartile-based spread metrics."""
    assert run([], label="x") == []
    assert run([1.0, 2.0, 3.0], label="x") == []
