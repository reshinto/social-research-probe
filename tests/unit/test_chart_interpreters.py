"""Tests for the deterministic chart-takeaway interpreters."""

from __future__ import annotations

from social_research_probe.pipeline.charts import (
    _chart_takeaways,
    _interpret_distribution,
    _interpret_outlier,
    _interpret_regression,
    _interpret_strongest_correlation,
    _strength_label,
)


def _item(trust, trend, opp, overall, velocity=10.0, engagement=0.05, age=5.0, title="x"):
    return {
        "title": title,
        "channel": "c",
        "url": "u",
        "scores": {"trust": trust, "trend": trend, "opportunity": opp, "overall": overall},
        "features": {
            "view_velocity": velocity,
            "engagement_ratio": engagement,
            "age_days": age,
            "subscriber_count": 100.0,
        },
    }


def test_takeaways_empty_dataset_returns_empty():
    assert _chart_takeaways([]) == []


def test_takeaways_includes_distribution_and_regressions():
    items = [
        _item(0.9, 0.8, 0.7, 0.85),
        _item(0.5, 0.6, 0.4, 0.55),
        _item(0.1, 0.2, 0.3, 0.20),
    ]
    out = _chart_takeaways(items)
    text = " | ".join(out)
    assert "Overall distribution" in text
    assert "Trust vs opportunity" in text
    assert "Trust vs trend" in text
    assert "Feature correlations" in text


def test_distribution_format():
    line = _interpret_distribution("overall", [0.1, 0.5, 0.9])
    assert "n=3" in line
    assert "min=0.10" in line
    assert "max=0.90" in line


def test_regression_too_few_points():
    line = _interpret_regression("a", "b", [1.0], [2.0])
    assert "too few points" in line


def test_regression_zero_variance():
    line = _interpret_regression("a", "b", [1.0, 1.0, 1.0], [2.0, 3.0, 4.0])
    assert "undefined" in line


def test_regression_strong_positive():
    xs = [0.1, 0.5, 0.9]
    ys = [0.2, 0.5, 0.8]
    line = _interpret_regression("trust", "trend", xs, ys)
    assert "strong positive" in line
    assert "slope=+" in line


def test_strength_label_buckets():
    assert _strength_label(0.95) == "strong"
    assert _strength_label(0.5) == "moderate"
    assert _strength_label(0.25) == "weak"
    assert _strength_label(0.05) == "negligible"


def test_strongest_correlation_returns_pair():
    items = [_item(i / 10, i / 10, i / 10, i / 10, velocity=i) for i in range(1, 6)]
    line = _interpret_strongest_correlation(items)
    assert "strongest pair" in line
    assert "↔" in line


def test_outlier_flag_when_extreme(monkeypatch):
    items = [_item(0.5, 0.5, 0.5, 0.5) for _ in range(5)]
    items.append(_item(0.5, 0.5, 0.5, 0.99, title="anomaly spike"))
    overall = [d["scores"]["overall"] for d in items]
    line = _interpret_outlier(items, overall)
    assert line is not None
    assert "anomaly spike" in line
    assert "z=" in line


def test_outlier_returns_none_when_no_extreme():
    items = [_item(0.5, 0.5, 0.5, 0.5 + i * 0.01) for i in range(5)]
    overall = [d["scores"]["overall"] for d in items]
    assert _interpret_outlier(items, overall) is None
