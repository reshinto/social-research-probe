"""Tests for claim quality assessment metrics."""

from __future__ import annotations

from tests.evals.assess_claims_quality import (
    duplicate_claim_rate,
    expected_type_coverage,
    grounded_claim_rate,
    hallucination_risk_rate,
    needs_review_rate,
    should_extract_coverage,
    should_not_extract_violation_rate,
    valid_claim_rate,
)
from tests.evals.claim_fixtures import CASES, MINIMUM_REQUIRED_FIELDS, ClaimEvalCase


def _perfect_claim() -> dict:
    return {
        "claim_id": "c1",
        "source_id": "s1",
        "source_url": "https://example.com/1",
        "source_title": "Title",
        "claim_text": "Revenue grew 42% last year",
        "claim_type": "fact_claim",
        "confidence": 0.95,
        "evidence_layer": "transcript",
        "evidence_tier": "metadata_transcript",
        "needs_corroboration": True,
        "corroboration_status": "pending",
        "needs_review": True,
        "extraction_method": "deterministic",
        "position_in_text": 10,
        "extracted_at": "2026-01-01T00:00:00",
    }


def _minimal_claim() -> dict:
    return {
        "claim_id": "c1",
        "claim_text": "something",
        "claim_type": "fact_claim",
    }


class TestValidClaimRate:
    def test_perfect_claims(self):
        claims = [_perfect_claim(), _perfect_claim()]
        assert valid_claim_rate(claims) == 1.0

    def test_missing_fields_below_one(self):
        claims = [_perfect_claim(), _minimal_claim()]
        assert valid_claim_rate(claims) < 1.0

    def test_empty_input(self):
        assert valid_claim_rate([]) == 0.0


class TestExpectedTypeCoverage:
    def test_all_types_found(self):
        claims = [
            {"claim_type": "fact_claim"},
            {"claim_type": "opinion"},
        ]
        assert expected_type_coverage(claims, {"fact_claim", "opinion"}) == 1.0

    def test_partial_coverage(self):
        claims = [{"claim_type": "fact_claim"}]
        assert expected_type_coverage(claims, {"fact_claim", "opinion"}) == 0.5

    def test_no_expected_types(self):
        assert expected_type_coverage([], set()) == 1.0

    def test_empty_claims(self):
        assert expected_type_coverage([], {"fact_claim"}) == 0.0


class TestShouldExtractCoverage:
    def test_all_phrases_found(self):
        claims = [{"claim_text": "Revenue grew 42% in 15 countries"}]
        assert should_extract_coverage(claims, ["42%", "15 countries"]) == 1.0

    def test_partial_found(self):
        claims = [{"claim_text": "Revenue grew 42%"}]
        assert should_extract_coverage(claims, ["42%", "15 countries"]) == 0.5

    def test_no_phrases(self):
        assert should_extract_coverage([], []) == 1.0

    def test_empty_claims(self):
        assert should_extract_coverage([], ["42%"]) == 0.0


class TestShouldNotExtractViolationRate:
    def test_clean(self):
        claims = [{"claim_text": "Revenue grew 42%"}]
        assert should_not_extract_violation_rate(claims, ["subscribe", "bell"]) == 0.0

    def test_violation(self):
        claims = [{"claim_text": "subscribe to the channel"}]
        assert should_not_extract_violation_rate(claims, ["subscribe", "bell"]) == 0.5

    def test_no_phrases(self):
        assert should_not_extract_violation_rate([], []) == 0.0

    def test_empty_claims(self):
        assert should_not_extract_violation_rate([], ["subscribe"]) == 0.0


class TestDuplicateClaimRate:
    def test_no_dupes(self):
        claims = [{"claim_id": "c1"}, {"claim_id": "c2"}]
        assert duplicate_claim_rate(claims) == 0.0

    def test_with_dupes(self):
        claims = [{"claim_id": "c1"}, {"claim_id": "c1"}, {"claim_id": "c2"}]
        assert duplicate_claim_rate(claims) > 0.0

    def test_empty(self):
        assert duplicate_claim_rate([]) == 0.0


class TestGroundedClaimRate:
    def test_all_grounded(self):
        claims = [{"position_in_text": 5}, {"position_in_text": 10}]
        assert grounded_claim_rate(claims) == 1.0

    def test_none_grounded(self):
        claims = [{"position_in_text": 0}, {"position_in_text": 0}]
        assert grounded_claim_rate(claims) == 0.0

    def test_mixed(self):
        claims = [{"position_in_text": 5}, {"position_in_text": 0}]
        assert grounded_claim_rate(claims) == 0.5

    def test_empty(self):
        assert grounded_claim_rate([]) == 0.0


class TestNeedsReviewRate:
    def test_all_flagged(self):
        claims = [{"needs_review": True}, {"needs_review": True}]
        assert needs_review_rate(claims) == 1.0

    def test_none_flagged(self):
        claims = [{"needs_review": False}, {"needs_review": False}]
        assert needs_review_rate(claims) == 0.0

    def test_returns_float(self):
        claims = [{"needs_review": True}, {"needs_review": False}]
        result = needs_review_rate(claims)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_empty(self):
        assert needs_review_rate([]) == 0.0


class TestHallucinationRiskRate:
    def test_ungrounded_high_confidence(self):
        claims = [{"position_in_text": 0, "confidence": 0.9}]
        assert hallucination_risk_rate(claims) == 1.0

    def test_grounded_high_confidence(self):
        claims = [{"position_in_text": 5, "confidence": 0.9}]
        assert hallucination_risk_rate(claims) == 0.0

    def test_ungrounded_low_confidence(self):
        claims = [{"position_in_text": 0, "confidence": 0.5}]
        assert hallucination_risk_rate(claims) == 0.0

    def test_empty(self):
        assert hallucination_risk_rate([]) == 0.0


class TestFixturesIntegrity:
    def test_all_cases_populated(self):
        for case in CASES:
            assert isinstance(case, ClaimEvalCase)
            assert case.case_id
            assert case.source_id
            assert case.evidence_layer
            assert case.evidence_tier

    def test_minimum_required_fields_count(self):
        assert len(MINIMUM_REQUIRED_FIELDS) == 15
