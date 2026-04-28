"""Tests for services.scoring (compute, weights)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import social_research_probe.services.scoring as compute
import social_research_probe.services.scoring as weights
from social_research_probe.platforms import EngagementMetrics, RawItem
from social_research_probe.utils.purposes.merge import MergedPurpose


class TestZscores:
    def test_too_few(self):
        assert compute.zscores([1.0]) == [0.0]

    def test_basic(self):
        out = compute.zscores([1.0, 2.0, 3.0])
        assert len(out) == 3
        assert sum(out) < 1e-9


class TestChannelCredibility:
    def test_no_subscribers(self):
        assert compute.channel_credibility(None) == 0.3
        assert compute.channel_credibility(0) == 0.3

    def test_log_scale(self):
        assert compute.channel_credibility(10) > 0
        assert compute.channel_credibility(1_000_000) <= 1.0


class TestAgeDays:
    def test_non_datetime(self):
        assert compute.age_days(None) == 30.0

    def test_datetime(self):
        ten_days_ago = datetime.now(UTC) - timedelta(days=10)
        assert 9.0 <= compute.age_days(ten_days_ago) <= 11.0


class TestNormalizeItem:
    def test_dict_passthrough(self):
        assert compute.normalize_item({"a": 1}) == {"a": 1}

    def test_invalid_returns_none(self):
        assert compute.normalize_item("not raw") is None

    def test_raw_item(self):
        raw = RawItem(
            id="1",
            url="https://x",
            title="t",
            author_id="a",
            author_name="A",
            published_at=None,
            metrics={"v": 1},
            text_excerpt="",
            thumbnail="",
            extras={"e": 1},
        )
        out = compute.normalize_item(raw)
        assert out and out["id"] == "1"
        assert out["channel"] == "A"


def test_compute_trust_basic():
    out = compute.compute_trust({"channel_subscribers": 1000})
    assert 0.0 <= out <= 1.0


def test_compute_trend_in_range():
    out = compute.compute_trend(0.1, 0.1, 0.1, 5.0)
    assert 0.0 <= out <= 1.0


def test_compute_opportunity_in_range():
    out = compute.compute_opportunity(0.1, 0.5, 30.0)
    assert 0.0 <= out <= 1.0


def test_build_features_keys():
    out = compute.build_features(1.0, 0.5, 5.0, 100)
    assert set(out.keys()) == {"view_velocity", "engagement_ratio", "age_days", "subscriber_count"}


def test_score_items_empty():
    assert compute.score_items([], []) == []


def test_score_items_with_dicts():
    items = [
        {"id": "1", "extras": {"channel_subscribers": 100}, "published_at": None},
        {"id": "2", "extras": {"channel_subscribers": 200}, "published_at": None},
    ]

    def _em(velocity, engagement, cross):
        return EngagementMetrics(
            views=None,
            likes=None,
            comments=None,
            upload_date=None,
            view_velocity=velocity,
            engagement_ratio=engagement,
            comment_velocity=None,
            cross_channel_repetition=cross,
        )

    metrics = [_em(1.0, 0.05, 0.1), _em(0.5, 0.02, 0.0)]
    out = compute.score_items(items, metrics)
    assert len(out) == 2
    assert out[0]["scores"]["overall"] >= out[1]["scores"]["overall"]


class TestResolveScoringWeights:
    def _purpose(self, overrides=None):
        return MergedPurpose(
            names=("x",),
            method="m",
            evidence_priorities=(),
            scoring_overrides=overrides or {},
        )

    def test_defaults(self, monkeypatch):
        cfg = MagicMock()
        cfg.raw = {}
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        out = weights.resolve_scoring_weights(self._purpose())
        assert set(out.keys()) == {"trust", "trend", "opportunity"}

    def test_config_override(self, monkeypatch):
        cfg = SimpleNamespace(raw={"scoring": {"weights": {"trust": 0.9}}})
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        out = weights.resolve_scoring_weights(self._purpose())
        assert out["trust"] == 0.9

    def test_purpose_override_wins(self, monkeypatch):
        cfg = SimpleNamespace(raw={"scoring": {"weights": {"trust": 0.9}}})
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        out = weights.resolve_scoring_weights(self._purpose({"trust": 0.5}))
        assert out["trust"] == 0.5
