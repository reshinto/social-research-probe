from hypothesis import given
from hypothesis import strategies as st

from social_research_probe.scoring.combine import overall_score

unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

@given(trust_lo=unit, trust_hi=unit, trend=unit, opp=unit)
def test_trust_dominates_trend(trust_lo, trust_hi, trend, opp):
    lo = overall_score(trust=min(trust_lo, trust_hi), trend=trend, opportunity=opp)
    hi = overall_score(trust=max(trust_lo, trust_hi), trend=trend, opportunity=opp)
    assert hi >= lo
