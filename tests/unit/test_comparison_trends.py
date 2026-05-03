"""Tests for trend signal derivation."""

from __future__ import annotations

from social_research_probe.utils.comparison.trends import derive_trends
from social_research_probe.utils.comparison.types import ClaimChange, NarrativeChange


def _narr_change(
    narrative_id: str = "n1",
    status: str = "repeated",
    cluster_type: str = "theme",
    strength_signal: str = "stable",
    risk_change: float = 0.0,
    opportunity_change: float = 0.0,
    claim_count_change: int = 0,
    title: str = "Test Narrative",
) -> NarrativeChange:
    return NarrativeChange(
        narrative_id=narrative_id,
        title=title,
        cluster_type=cluster_type,
        status=status,
        match_method="exact_id",
        matched_id=narrative_id,
        confidence_change=0.0,
        opportunity_change=opportunity_change,
        risk_change=risk_change,
        claim_count_change=claim_count_change,
        source_count_change=0,
        strength_signal=strength_signal,
    )


def _claim_change(
    claim_id: str = "c1",
    status: str = "repeated",
    corroboration_changed: bool = False,
    baseline_corroboration: str = "pending",
    target_corroboration: str = "pending",
) -> ClaimChange:
    return ClaimChange(
        claim_id=claim_id,
        claim_text="test",
        claim_type="fact_claim",
        source_url="",
        status=status,
        confidence_change=0.0,
        corroboration_changed=corroboration_changed,
        baseline_corroboration=baseline_corroboration,
        target_corroboration=target_corroboration,
        review_status_changed=False,
    )


class TestDeriveTrends:
    def test_empty_inputs(self) -> None:
        assert derive_trends([], []) == []

    def test_emerging_narrative(self) -> None:
        narr = [_narr_change(status="new", claim_count_change=5)]
        result = derive_trends(narr, [])
        assert len(result) == 1
        assert result[0]["signal_type"] == "emerging_narrative"

    def test_emerging_narrative_below_threshold(self) -> None:
        narr = [_narr_change(status="new", claim_count_change=2)]
        result = derive_trends(narr, [])
        assert len(result) == 0

    def test_rising_risk(self) -> None:
        narr = [_narr_change(risk_change=0.2)]
        result = derive_trends(narr, [])
        assert len(result) == 1
        assert result[0]["signal_type"] == "rising_risk"

    def test_rising_risk_below_threshold(self) -> None:
        narr = [_narr_change(risk_change=0.1)]
        assert derive_trends(narr, []) == []

    def test_growing_opportunity(self) -> None:
        narr = [_narr_change(opportunity_change=0.2)]
        result = derive_trends(narr, [])
        assert len(result) == 1
        assert result[0]["signal_type"] == "growing_opportunity"

    def test_growing_opportunity_below_threshold(self) -> None:
        narr = [_narr_change(opportunity_change=0.1)]
        assert derive_trends(narr, []) == []

    def test_weakening_narrative(self) -> None:
        narr = [_narr_change(strength_signal="weakened")]
        result = derive_trends(narr, [])
        assert len(result) == 1
        assert result[0]["signal_type"] == "weakening_narrative"

    def test_rising_objections_new(self) -> None:
        narr = [_narr_change(status="new", cluster_type="objection")]
        result = derive_trends(narr, [])
        assert any(s["signal_type"] == "rising_objections" for s in result)

    def test_rising_objections_strengthened(self) -> None:
        narr = [_narr_change(cluster_type="objection", strength_signal="strengthened")]
        result = derive_trends(narr, [])
        assert any(s["signal_type"] == "rising_objections" for s in result)

    def test_claim_surge(self) -> None:
        claims = [
            _claim_change(f"c{i}", status="repeated") for i in range(3)
        ] + [
            _claim_change(f"new{i}", status="new") for i in range(5)
        ]
        result = derive_trends([], claims)
        assert any(s["signal_type"] == "claim_surge" for s in result)

    def test_no_claim_surge_below_threshold(self) -> None:
        claims = [
            _claim_change(f"c{i}", status="repeated") for i in range(5)
        ] + [
            _claim_change("new1", status="new"),
        ]
        result = derive_trends([], claims)
        assert not any(s["signal_type"] == "claim_surge" for s in result)

    def test_improving_corroboration(self) -> None:
        claims = [
            _claim_change(f"c{i}", status="repeated", corroboration_changed=True,
                          baseline_corroboration="pending", target_corroboration="confirmed")
            for i in range(4)
        ] + [
            _claim_change("c99", status="repeated"),
        ]
        result = derive_trends([], claims)
        assert any(s["signal_type"] == "improving_corroboration" for s in result)

    def test_weakening_corroboration(self) -> None:
        claims = [
            _claim_change(f"c{i}", status="repeated", corroboration_changed=True,
                          baseline_corroboration="confirmed", target_corroboration="pending")
            for i in range(4)
        ] + [
            _claim_change("c99", status="repeated"),
        ]
        result = derive_trends([], claims)
        assert any(s["signal_type"] == "weakening_corroboration" for s in result)

    def test_sorted_by_score_desc(self) -> None:
        narr = [
            _narr_change("n1", strength_signal="weakened"),
            _narr_change("n2", status="new", claim_count_change=5),
        ]
        result = derive_trends(narr, [])
        assert result[0]["score"] >= result[1]["score"]

    def test_cap_at_10(self) -> None:
        narr = [
            _narr_change(f"n{i}", risk_change=0.2 + i * 0.01)
            for i in range(15)
        ]
        result = derive_trends(narr, [])
        assert len(result) <= 10
