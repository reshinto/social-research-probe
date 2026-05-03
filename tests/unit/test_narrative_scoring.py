"""Tests for narrative cluster scoring functions."""

from __future__ import annotations

from social_research_probe.utils.narratives.scoring import (
    compute_confidence,
    compute_opportunity_score,
    compute_risk_score,
)


def _claim(
    confidence: float = 0.7,
    corroboration_status: str = "pending",
    contradiction_status: str = "none",
    needs_review: bool = False,
    source_id: str = "s1",
) -> dict:
    return {
        "confidence": confidence,
        "corroboration_status": corroboration_status,
        "contradiction_status": contradiction_status,
        "needs_review": needs_review,
        "_source_id": source_id,
    }


class TestComputeConfidence:
    def test_empty_returns_zero(self) -> None:
        assert compute_confidence([]) == 0.0

    def test_single_claim(self) -> None:
        assert compute_confidence([_claim(confidence=0.8)]) == 0.8

    def test_mean_of_multiple(self) -> None:
        claims = [_claim(confidence=0.6), _claim(confidence=0.8)]
        assert compute_confidence(claims) == 0.7

    def test_missing_confidence_defaults_to_half(self) -> None:
        assert compute_confidence([{"claim_id": "c1"}]) == 0.5

    def test_clamped_to_unit_interval(self) -> None:
        assert compute_confidence([_claim(confidence=1.5)]) == 1.0


class TestComputeOpportunityScore:
    def test_empty_returns_zero(self) -> None:
        assert compute_opportunity_score([], "theme") == 0.0

    def test_opportunity_type_gets_base_boost(self) -> None:
        claims = [_claim(corroboration_status="pending")]
        opp = compute_opportunity_score(claims, "opportunity")
        theme = compute_opportunity_score(claims, "theme")
        assert opp > theme

    def test_supported_claims_increase_score(self) -> None:
        supported = [_claim(corroboration_status="supported")]
        pending = [_claim(corroboration_status="pending")]
        assert compute_opportunity_score(supported, "theme") > compute_opportunity_score(
            pending, "theme"
        )

    def test_source_diversity_increases_score(self) -> None:
        one_source = [_claim(source_id="s1"), _claim(source_id="s1")]
        two_sources = [_claim(source_id="s1"), _claim(source_id="s2")]
        assert compute_opportunity_score(two_sources, "theme") > compute_opportunity_score(
            one_source, "theme"
        )

    def test_clamped_to_one(self) -> None:
        claims = [_claim(corroboration_status="supported", source_id=f"s{i}") for i in range(20)]
        assert compute_opportunity_score(claims, "opportunity") <= 1.0


class TestComputeRiskScore:
    def test_empty_returns_zero(self) -> None:
        assert compute_risk_score([], "theme") == 0.0

    def test_risk_type_gets_base_boost(self) -> None:
        claims = [_claim()]
        risk = compute_risk_score(claims, "risk")
        theme = compute_risk_score(claims, "theme")
        assert risk > theme

    def test_contradictions_increase_score(self) -> None:
        contradicted = [_claim(contradiction_status="contradicted")]
        clean = [_claim(contradiction_status="none")]
        assert compute_risk_score(contradicted, "theme") > compute_risk_score(clean, "theme")

    def test_needs_review_increases_score(self) -> None:
        review = [_claim(needs_review=True)]
        no_review = [_claim(needs_review=False)]
        assert compute_risk_score(review, "theme") > compute_risk_score(no_review, "theme")

    def test_clamped_to_one(self) -> None:
        claims = [
            _claim(
                contradiction_status="contradicted",
                needs_review=True,
                corroboration_status="contradicted",
            )
            for _ in range(10)
        ]
        assert compute_risk_score(claims, "objection") <= 1.0
