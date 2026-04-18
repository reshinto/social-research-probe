import math
from social_research_probe.scoring.trust import trust_score
from social_research_probe.scoring.trend import trend_score, recency_decay
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.combine import overall_score

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
