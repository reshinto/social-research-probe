"""Tests for tech.scoring (combine, opportunity, trend, trust, normalize)."""

from __future__ import annotations

from datetime import UTC, datetime

from social_research_probe.technologies.scoring import score_one
from social_research_probe.technologies.scoring.combine import (
    DEFAULT_WEIGHTS,
    overall_score,
)
from social_research_probe.technologies.scoring.opportunity import opportunity_score
from social_research_probe.technologies.scoring.trend import recency_decay, trend_score
from social_research_probe.technologies.scoring.trust import trust_score
from social_research_probe.utils.core.types import RawItem
from social_research_probe.utils.pipeline.helpers import normalize_item


class TestOverallScore:
    def test_default_weights(self):
        s = overall_score(trust=1.0, trend=1.0, opportunity=1.0)
        assert abs(s - 1.0) < 1e-9

    def test_zero_clipped(self):
        assert overall_score(trust=-1.0, trend=-1.0, opportunity=-1.0) == 0.0

    def test_custom_weights_partial(self):
        s = overall_score(trust=1.0, trend=0.0, opportunity=0.0, weights={"trust": 1.0})
        assert s == 1.0

    def test_default_weights_sum_one(self):
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


class TestOpportunity:
    def test_perfect(self):
        s = opportunity_score(market_gap=1.0, monetization_proxy=1.0, feasibility=1.0, novelty=1.0)
        assert abs(s - 1.0) < 1e-9

    def test_zero(self):
        assert (
            opportunity_score(market_gap=0.0, monetization_proxy=0.0, feasibility=0.0, novelty=0.0)
            == 0.0
        )

    def test_clipped_above(self):
        s = opportunity_score(market_gap=2.0, monetization_proxy=2.0, feasibility=2.0, novelty=2.0)
        assert s == 1.0


class TestTrend:
    def test_recency_today(self):
        assert recency_decay(0.0) == 1.0

    def test_recency_old_decays(self):
        assert recency_decay(60.0) < recency_decay(0.0)

    def test_recency_negative_clamped(self):
        assert recency_decay(-5.0) == 1.0

    def test_trend_score_in_range(self):
        s = trend_score(
            z_view_velocity=1.0,
            z_engagement_ratio=0.0,
            z_cross_channel_repetition=-1.0,
            age_days=10.0,
        )
        assert 0.0 <= s <= 1.0


class TestTrust:
    def test_perfect(self):
        s = trust_score(
            source_class=1.0,
            channel_credibility=1.0,
            citation_traceability=1.0,
            ai_slop_penalty=0.0,
            corroboration_score=1.0,
        )
        assert abs(s - 1.0) < 1e-9

    def test_zero(self):
        s = trust_score(
            source_class=0.0,
            channel_credibility=0.0,
            citation_traceability=0.0,
            ai_slop_penalty=1.0,
            corroboration_score=0.0,
        )
        assert s == 0.0


class TestZscores:
    def test_two_values_produces_nonzero(self):
        result = __import__(
            "social_research_probe.technologies.scoring", fromlist=["zscores"]
        ).zscores([1.0, 3.0])
        assert len(result) == 2
        assert result[0] < 0 and result[1] > 0

    def test_single_value_returns_zero(self):
        from social_research_probe.technologies.scoring import zscores

        assert zscores([5.0]) == [0.0]


class TestChannelCredibility:
    def test_with_subscribers_returns_scaled(self):
        from social_research_probe.technologies.scoring import channel_credibility

        assert channel_credibility(1_000_000) > 0.3

    def test_none_returns_default(self):
        from social_research_probe.technologies.scoring import channel_credibility

        assert channel_credibility(None) == 0.3


class TestMetricValues:
    def test_with_metrics_returns_values(self):
        from social_research_probe.technologies.scoring import _metric_values
        from social_research_probe.utils.core.types import EngagementMetrics

        m = EngagementMetrics(
            views=None,
            likes=None,
            comments=None,
            upload_date=None,
            view_velocity=1.0,
            engagement_ratio=0.5,
            comment_velocity=None,
            cross_channel_repetition=0.2,
        )
        result = _metric_values(m)
        assert result == (1.0, 0.5, 0.2)


def _make_raw_item(**overrides):
    defaults = {
        "id": "vid1",
        "url": "https://youtube.com/watch?v=vid1",
        "title": "Test Video",
        "author_id": "ch1",
        "author_name": "Channel",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC),
        "metrics": {},
        "text_excerpt": "Video description text",
        "thumbnail": "https://img.youtube.com/vi/vid1/default.jpg",
        "extras": {"channel_subscribers": 1000},
    }
    defaults.update(overrides)
    return RawItem(**defaults)


class TestNormalizeItem:
    def test_preserves_text_excerpt(self):
        result = normalize_item(_make_raw_item())
        assert result["text_excerpt"] == "Video description text"

    def test_preserves_thumbnail(self):
        result = normalize_item(_make_raw_item())
        assert result["thumbnail"] == "https://img.youtube.com/vi/vid1/default.jpg"

    def test_text_excerpt_none(self):
        result = normalize_item(_make_raw_item(text_excerpt=None))
        assert result["text_excerpt"] is None

    def test_thumbnail_none(self):
        result = normalize_item(_make_raw_item(thumbnail=None))
        assert result["thumbnail"] is None

    def test_dict_passthrough_unchanged(self):
        d = {"id": "x", "title": "Y", "custom_field": 42}
        assert normalize_item(d) is d

    def test_non_raw_item_returns_none(self):
        assert normalize_item("not an item") is None

    def test_existing_fields_preserved(self):
        result = normalize_item(_make_raw_item())
        assert result["id"] == "vid1"
        assert result["url"] == "https://youtube.com/watch?v=vid1"
        assert result["title"] == "Test Video"
        assert result["channel"] == "Channel"
        assert result["author_id"] == "ch1"
        assert result["extras"]["channel_subscribers"] == 1000


class TestScoreOnePreservesMetadata:
    def test_text_excerpt_survives_scoring(self):
        item = normalize_item(_make_raw_item())
        scored = score_one(item, None, 0.0, 0.0, DEFAULT_WEIGHTS)
        assert scored["text_excerpt"] == "Video description text"

    def test_thumbnail_survives_scoring(self):
        item = normalize_item(_make_raw_item())
        scored = score_one(item, None, 0.0, 0.0, DEFAULT_WEIGHTS)
        assert scored["thumbnail"] == "https://img.youtube.com/vi/vid1/default.jpg"

    def test_scores_unaffected_by_metadata(self):
        item_with = normalize_item(_make_raw_item())
        item_without = normalize_item(_make_raw_item(text_excerpt=None, thumbnail=None))
        scored_with = score_one(item_with, None, 0.0, 0.0, DEFAULT_WEIGHTS)
        scored_without = score_one(item_without, None, 0.0, 0.0, DEFAULT_WEIGHTS)
        assert scored_with["scores"] == scored_without["scores"]
