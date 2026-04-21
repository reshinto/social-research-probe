"""Evidence tests — scoring services produce formula-verified outputs.

Five pure-math services are covered: trust, trend, opportunity, overall
combiner, plus invariants (clip, monotonicity) that must hold for any
valid input. Every expected value is either computed inline by the test
from the formula in source or stated as an identity (all-ones inputs
give 1.0, all-zeros give 0.0).

Evidence receipt — each test docstring cites the formula source:

| Service | Formula source | Reference |
| --- | --- | --- |
| trust_score | scoring/trust.py:5-19 | weighted sum of five factors |
| recency_decay | scoring/trend.py:8-9 | exp(-max(0, age) / 30) |
| trend_score | scoring/trend.py:12-27 | 0.4/0.2/0.2/0.2 split over z-normed + recency |
| opportunity_score | scoring/opportunity.py:5-10 | 0.4/0.3/0.2/0.1 weighted sum |
| overall_score | scoring/combine.py:7, 14-27 | default 0.45/0.30/0.25, overrideable |

Tolerances: ``pytest.approx(rel=1e-9, abs=1e-12)`` for pure arithmetic; no
soft lower-bound assertions.
"""

from __future__ import annotations

import math

import pytest

from social_research_probe.scoring.combine import DEFAULT_WEIGHTS, overall_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.trend import recency_decay, trend_score
from social_research_probe.scoring.trust import trust_score

_APPROX = {"rel": 1e-9, "abs": 1e-12}


# ---------------------------------------------------------------------------
# trust_score — scoring/trust.py:5-19
# Formula: 0.35*source_class + 0.25*channel_credibility + 0.15*citation_traceability
#        + 0.15*(1 - ai_slop_penalty) + 0.10*corroboration_score, clipped to [0, 1].
# ---------------------------------------------------------------------------


def test_trust_all_ones_gives_maximum_score():
    """All five inputs at 1.0 (except ai_slop_penalty=0) sums to exactly 1.0."""
    score = trust_score(
        source_class=1.0,
        channel_credibility=1.0,
        citation_traceability=1.0,
        ai_slop_penalty=0.0,
        corroboration_score=1.0,
    )
    assert score == pytest.approx(1.0, **_APPROX)


def test_trust_all_zeros_gives_minimum_score():
    """All factors at 0.0 with full ai-slop penalty sums to exactly 0.0."""
    score = trust_score(
        source_class=0.0,
        channel_credibility=0.0,
        citation_traceability=0.0,
        ai_slop_penalty=1.0,
        corroboration_score=0.0,
    )
    assert score == pytest.approx(0.0, **_APPROX)


def test_trust_mid_inputs_match_weighted_formula():
    """Reference value computed inline from the published weights."""
    inputs = dict(
        source_class=0.8,
        channel_credibility=0.6,
        citation_traceability=0.4,
        ai_slop_penalty=0.2,
        corroboration_score=0.5,
    )
    expected = (
        0.35 * inputs["source_class"]
        + 0.25 * inputs["channel_credibility"]
        + 0.15 * inputs["citation_traceability"]
        + 0.15 * (1.0 - inputs["ai_slop_penalty"])
        + 0.10 * inputs["corroboration_score"]
    )
    assert trust_score(**inputs) == pytest.approx(expected, **_APPROX)


@pytest.mark.parametrize(
    "overshoot_input",
    ["source_class", "channel_credibility", "citation_traceability"],
)
def test_trust_clips_above_one(overshoot_input):
    """No input combination can push the score above 1.0 — result is clipped."""
    kwargs = dict(
        source_class=1.0,
        channel_credibility=1.0,
        citation_traceability=1.0,
        ai_slop_penalty=0.0,
        corroboration_score=1.0,
    )
    kwargs[overshoot_input] = 5.0  # deliberately out of [0, 1]
    assert trust_score(**kwargs) == pytest.approx(1.0, **_APPROX)


# ---------------------------------------------------------------------------
# recency_decay — scoring/trend.py:8-9
# Formula: exp(-max(0, age_days) / 30)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "age_days, expected",
    [
        (0.0, 1.0),
        (30.0, math.exp(-1.0)),
        (90.0, math.exp(-3.0)),
        (-5.0, 1.0),  # negative age clamps to 0 — exp(0) = 1
    ],
)
def test_recency_decay_matches_exponential_formula(age_days, expected):
    assert recency_decay(age_days) == pytest.approx(expected, **_APPROX)


# ---------------------------------------------------------------------------
# trend_score — scoring/trend.py:12-27
# Formula: 0.40*norm_z(z_view) + 0.20*norm_z(z_eng) + 0.20*norm_z(z_cross) + 0.20*decay
#   where norm_z(z) = clip(0.5 + z/6) and decay = exp(-max(0, age)/30).
# ---------------------------------------------------------------------------


def _norm_z(z: float) -> float:
    return max(0.0, min(1.0, 0.5 + z / 6.0))


def test_trend_all_zero_z_and_fresh_video():
    """z=0 gives norm_z=0.5; age_days=0 gives decay=1; sum = 0.4*0.5+0.2*0.5+0.2*0.5+0.2*1 = 0.6."""
    score = trend_score(
        z_view_velocity=0.0,
        z_engagement_ratio=0.0,
        z_cross_channel_repetition=0.0,
        age_days=0.0,
    )
    expected = 0.4 * 0.5 + 0.2 * 0.5 + 0.2 * 0.5 + 0.2 * 1.0
    assert score == pytest.approx(expected, **_APPROX)


def test_trend_positive_z_with_stale_video():
    """z=2 gives norm_z≈0.833; age=365 gives decay=exp(-365/30)."""
    inputs = dict(
        z_view_velocity=2.0,
        z_engagement_ratio=1.0,
        z_cross_channel_repetition=-1.0,
        age_days=365.0,
    )
    expected = (
        0.40 * _norm_z(inputs["z_view_velocity"])
        + 0.20 * _norm_z(inputs["z_engagement_ratio"])
        + 0.20 * _norm_z(inputs["z_cross_channel_repetition"])
        + 0.20 * math.exp(-365.0 / 30.0)
    )
    assert trend_score(**inputs) == pytest.approx(expected, **_APPROX)


def test_trend_extreme_z_values_are_clipped_by_norm_z():
    """z=100 clips norm_z to 1.0; the score is bounded at 1.0 as age→0."""
    score = trend_score(
        z_view_velocity=100.0,
        z_engagement_ratio=100.0,
        z_cross_channel_repetition=100.0,
        age_days=0.0,
    )
    assert score == pytest.approx(1.0, **_APPROX)


# ---------------------------------------------------------------------------
# opportunity_score — scoring/opportunity.py:5-10
# Formula: 0.40*market_gap + 0.30*monetization_proxy + 0.20*feasibility + 0.10*novelty
# ---------------------------------------------------------------------------


def test_opportunity_all_ones():
    """All inputs at 1.0 sums to 0.4+0.3+0.2+0.1 = 1.0 exactly."""
    assert opportunity_score(
        market_gap=1.0, monetization_proxy=1.0, feasibility=1.0, novelty=1.0
    ) == pytest.approx(1.0, **_APPROX)


def test_opportunity_mid_inputs_match_weighted_formula():
    inputs = dict(
        market_gap=0.7, monetization_proxy=0.5, feasibility=0.9, novelty=0.3
    )
    expected = (
        0.40 * inputs["market_gap"]
        + 0.30 * inputs["monetization_proxy"]
        + 0.20 * inputs["feasibility"]
        + 0.10 * inputs["novelty"]
    )
    assert opportunity_score(**inputs) == pytest.approx(expected, **_APPROX)


# ---------------------------------------------------------------------------
# overall_score — scoring/combine.py:7, 14-27
# Default weights: trust=0.45, trend=0.30, opportunity=0.25.
# ---------------------------------------------------------------------------


def test_overall_default_weights_sum_to_one_for_unit_inputs():
    """(1, 1, 1) with default weights returns exactly 1.0."""
    assert overall_score(
        trust=1.0, trend=1.0, opportunity=1.0
    ) == pytest.approx(1.0, **_APPROX)


def test_overall_zero_inputs_return_zero():
    assert overall_score(
        trust=0.0, trend=0.0, opportunity=0.0
    ) == pytest.approx(0.0, **_APPROX)


def test_overall_applies_default_weights_per_axis():
    """(1, 0, 0) returns the default trust weight exactly."""
    assert overall_score(
        trust=1.0, trend=0.0, opportunity=0.0
    ) == pytest.approx(DEFAULT_WEIGHTS["trust"], **_APPROX)


def test_overall_custom_weights_override_defaults_only_for_given_keys():
    """Partial override: trust weight raised to 0.60, trend/opportunity keep defaults."""
    score = overall_score(
        trust=1.0,
        trend=0.5,
        opportunity=0.2,
        weights={"trust": 0.60},
    )
    expected = 0.60 * 1.0 + DEFAULT_WEIGHTS["trend"] * 0.5 + DEFAULT_WEIGHTS["opportunity"] * 0.2
    assert score == pytest.approx(expected, **_APPROX)


def test_overall_clips_above_one_when_weights_exceed_unit_sum():
    """User-supplied weights that sum > 1 with all-ones inputs still clip to 1.0."""
    score = overall_score(
        trust=1.0,
        trend=1.0,
        opportunity=1.0,
        weights={"trust": 1.0, "trend": 1.0, "opportunity": 1.0},
    )
    assert score == pytest.approx(1.0, **_APPROX)


# ---------------------------------------------------------------------------
# Invariants — properties that must hold for ANY valid input in [0, 1].
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "trust, trend, opportunity",
    [
        (0.0, 0.0, 0.0),
        (0.25, 0.5, 0.75),
        (1.0, 1.0, 1.0),
        (0.1, 0.9, 0.3),
        (0.5, 0.5, 0.5),
    ],
)
def test_overall_result_is_always_in_unit_interval(trust, trend, opportunity):
    """Property: overall_score(t, n, o) ∈ [0, 1] for any t, n, o ∈ [0, 1]."""
    score = overall_score(trust=trust, trend=trend, opportunity=opportunity)
    assert 0.0 <= score <= 1.0


@pytest.mark.parametrize("axis", ["trust", "trend", "opportunity"])
def test_overall_is_monotonic_per_axis(axis):
    """Property: raising one axis (others fixed) must not decrease the overall score."""
    base = {"trust": 0.3, "trend": 0.3, "opportunity": 0.3}
    higher = {**base, axis: 0.7}
    assert overall_score(**higher) >= overall_score(**base)


@pytest.mark.parametrize(
    "axis", ["source_class", "channel_credibility", "citation_traceability", "corroboration_score"]
)
def test_trust_is_monotonic_per_positive_axis(axis):
    """Property: raising any positive trust factor cannot decrease the score."""
    base = dict(
        source_class=0.3,
        channel_credibility=0.3,
        citation_traceability=0.3,
        ai_slop_penalty=0.5,
        corroboration_score=0.3,
    )
    higher = {**base, axis: 0.8}
    assert trust_score(**higher) >= trust_score(**base)


def test_trust_is_antitone_in_ai_slop_penalty():
    """Property: higher ai_slop_penalty must not increase the trust score."""
    base = dict(
        source_class=0.5,
        channel_credibility=0.5,
        citation_traceability=0.5,
        ai_slop_penalty=0.2,
        corroboration_score=0.5,
    )
    penalised = {**base, "ai_slop_penalty": 0.8}
    assert trust_score(**penalised) <= trust_score(**base)
