"""Tests for tech.scoring (combine, opportunity, trend, trust)."""

from __future__ import annotations

from social_research_probe.technologies.scoring.combine import (
    DEFAULT_WEIGHTS,
    overall_score,
)
from social_research_probe.technologies.scoring.opportunity import opportunity_score
from social_research_probe.technologies.scoring.trend import recency_decay, trend_score
from social_research_probe.technologies.scoring.trust import trust_score


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
