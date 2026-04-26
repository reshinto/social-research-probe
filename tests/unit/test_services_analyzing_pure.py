"""Tests for analyzing pure helpers: _dataset_key, derived_targets, charts_suite."""

from __future__ import annotations

from pathlib import Path

from social_research_probe.services.analyzing import (
    _dataset_key,
    charts_suite,
    derived_targets,
)


def test_dataset_key_stable():
    items = [{"id": "1", "overall_score": 0.5}, {"id": "2", "overall_score": 0.4}]
    a = _dataset_key.dataset_key(items, namespace="ns")
    b = _dataset_key.dataset_key(items, namespace="ns")
    assert a == b


def test_dataset_key_distinct_on_change():
    a = _dataset_key.dataset_key([{"id": "1", "overall_score": 0.5}], namespace="x")
    b = _dataset_key.dataset_key([{"id": "1", "overall_score": 0.6}], namespace="x")
    assert a != b


class TestDerivedTargets:
    def test_basic(self):
        items = [
            {
                "overall_score": 0.9,
                "trust": 0.8,
                "trend": 0.7,
                "opportunity": 0.6,
                "features": {
                    "view_velocity": 1.0,
                    "engagement_ratio": 0.05,
                    "age_days": 5.0,
                    "subscriber_count": 100.0,
                },
                "source_class": "primary",
            },
            {
                "overall_score": 0.5,
                "trust": 0.4,
                "trend": 0.3,
                "opportunity": 0.2,
                "features": {
                    "view_velocity": 2.0,
                    "engagement_ratio": 0.02,
                    "age_days": 10.0,
                    "subscriber_count": 50.0,
                },
                "source_class": "commentary",
            },
        ]
        out = derived_targets.build_targets(items)
        assert out["rank"] == [0.0, 1.0]
        assert out["is_top_n"][0] == 1
        assert out["overall"] == [0.9, 0.5]
        assert out["source_class"] == ["primary", "commentary"]
        assert out["views"][0] == 5.0  # 1.0 * 5.0
        assert out["event_crossed_100k"] == [0, 0]


class TestChartsSuite:
    def test_render_all_empty(self, tmp_path: Path):
        assert charts_suite.render_all([], tmp_path) == []

    def test_render_all_with_items(self, tmp_path: Path):
        items = [
            {
                "trust": 0.5,
                "trend": 0.4,
                "opportunity": 0.3,
                "overall_score": 0.5,
                "features": {"view_velocity": 1.0, "engagement_ratio": 0.05, "age_days": 5.0},
                "channel": "C1",
            },
            {
                "trust": 0.4,
                "trend": 0.3,
                "opportunity": 0.2,
                "overall_score": 0.4,
                "features": {"view_velocity": 2.0, "engagement_ratio": 0.04, "age_days": 10.0},
                "channel": "C2",
            },
        ]
        out = charts_suite.render_all(items, tmp_path)
        assert len(out) >= 1
        assert all("see PNG" in r.caption for r in out)

    def test_safe_render_swallows_errors(self):
        def fail():
            raise RuntimeError("nope")

        assert charts_suite._safe_render(fail) is None
