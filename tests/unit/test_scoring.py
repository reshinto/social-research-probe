import math

from social_research_probe.scoring.combine import overall_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.trend import recency_decay, trend_score
from social_research_probe.scoring.trust import trust_score


def test_trust_bounds_and_formula():
    s = trust_score(source_class=1.0, channel_credibility=1.0,
                    citation_traceability=1.0, ai_slop_penalty=0.0,
                    corroboration_score=1.0)
    assert math.isclose(s, 1.0, abs_tol=1e-9)

def test_trend_recency_decay_monotonic():
    assert recency_decay(0) > recency_decay(30) > recency_decay(365)

def test_opportunity_bounds():
    s = opportunity_score(market_gap=0.0, monetization_proxy=0.0,
                          feasibility=0.0, novelty=0.0)
    assert s == 0.0

def test_overall_weights_sum_to_one():
    s = overall_score(trust=1.0, trend=1.0, opportunity=1.0)
    assert math.isclose(s, 1.0, abs_tol=1e-9)


# --- Additional trend.py coverage (lines 3->exit, 10-11) ---

def test_clip_clamps_above_one():
    # Force extremely high z-scores so the weighted sum exceeds 1.0; _clip must cap it.
    s = trend_score(z_view_velocity=100.0, z_engagement_ratio=100.0,
                    z_cross_channel_repetition=100.0, age_days=0.0)
    assert s == 1.0


def test_clip_clamps_below_zero():
    # Force extremely negative z-scores and a very old age so the sum goes below 0.0.
    s = trend_score(z_view_velocity=-100.0, z_engagement_ratio=-100.0,
                    z_cross_channel_repetition=-100.0, age_days=99999.0)
    assert s == 0.0


def test_norm_z_inner_function_called():
    # Exercises norm_z with typical z values (covers lines 10-11).
    s = trend_score(z_view_velocity=1.0, z_engagement_ratio=0.5,
                    z_cross_channel_repetition=0.0, age_days=7.0)
    assert 0.0 <= s <= 1.0
