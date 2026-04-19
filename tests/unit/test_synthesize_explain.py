"""Tests for synthesize.explain plain-English readings of stats results."""

from __future__ import annotations

from social_research_probe.stats.base import StatResult
from social_research_probe.synthesize.explain import explain


def _r(name: str, value: float, caption: str = "c") -> StatResult:
    return StatResult(name=name, value=value, caption=caption)


def test_unknown_name_returns_bare_caption():
    assert explain(_r("mystery_metric", 1.0, "x")) == "x"


def test_growth_rate_flat():
    out = explain(_r("growth_rate", 0.001))
    assert "essentially flat" in out


def test_growth_rate_rising():
    out = explain(_r("growth_rate", 0.05))
    assert "rising" in out


def test_growth_rate_falling():
    out = explain(_r("growth_rate", -0.05))
    assert "falling" in out


def test_slope_flat():
    out = explain(_r("slope", 0.0))
    assert "no meaningful linear trend" in out


def test_slope_rising_and_falling():
    assert "increases" in explain(_r("slope", 0.5))
    assert "decreases" in explain(_r("slope", -0.5))


def test_r_squared_buckets():
    assert "strong fit" in explain(_r("r_squared", 0.9))
    assert "moderate fit" in explain(_r("r_squared", 0.6))
    assert "weak fit" in explain(_r("r_squared", 0.3))
    assert "no real linear pattern" in explain(_r("r_squared", 0.05))


def test_pearson_buckets():
    assert "no meaningful correlation" in explain(_r("pearson_r", 0.05))
    assert "weak correlation" in explain(_r("pearson_r", 0.2))
    assert "moderate correlation" in explain(_r("pearson_r", 0.5))
    assert "strong correlation" in explain(_r("pearson_r", 0.9))
    assert "tends to fall" in explain(_r("pearson_r", -0.5))


def test_outlier_count_zero_and_some():
    assert "no extreme items" in explain(_r("outlier_count", 0))
    assert "review them" in explain(_r("outlier_count", 2))


def test_outlier_fraction_zero_and_nonzero():
    assert "well-behaved" in explain(_r("outlier_fraction", 0.0))
    assert "%" in explain(_r("outlier_fraction", 0.4))


def test_iqr_and_range_readings():
    assert "tightly clustered" in explain(_r("iqr", 0.05))
    assert "best and worst" in explain(_r("range", 0.5))


def test_descriptive_readings():
    assert "average" in explain(_r("mean_score", 0.5))
    assert "middle" in explain(_r("median_score", 0.5))


def test_stdev_buckets():
    assert "tight clustering" in explain(_r("stdev_x", 0.01))
    assert "moderate variation" in explain(_r("stdev_x", 0.1))
    assert "wide spread" in explain(_r("stdev_x", 0.5))
