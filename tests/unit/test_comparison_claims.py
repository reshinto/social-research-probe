"""Tests for claim comparison algorithm."""

from __future__ import annotations

from social_research_probe.utils.comparison.claims import compare_claims, normalize_claim_text


def _claim(
    claim_id: str = "c1",
    claim_text: str = "Some claim",
    confidence: float = 0.8,
    corroboration_status: str = "supported",
    needs_review: int = 0,
    claim_type: str = "fact_claim",
    source_url: str = "https://example.com",
) -> dict:
    return {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "claim_type": claim_type,
        "source_url": source_url,
        "confidence": confidence,
        "corroboration_status": corroboration_status,
        "needs_review": needs_review,
    }


class TestNormalizeClaimText:
    def test_case_insensitive(self) -> None:
        assert normalize_claim_text("Hello World") == normalize_claim_text("hello world")

    def test_whitespace_collapsed(self) -> None:
        assert normalize_claim_text("a  b   c") == normalize_claim_text("a b c")

    def test_strips_leading_trailing(self) -> None:
        assert normalize_claim_text("  hello  ") == normalize_claim_text("hello")

    def test_deterministic(self) -> None:
        h1 = normalize_claim_text("test claim")
        h2 = normalize_claim_text("test claim")
        assert h1 == h2
        assert len(h1) == 16

    def test_different_text_different_hash(self) -> None:
        assert normalize_claim_text("claim A") != normalize_claim_text("claim B")


class TestCompareClaims:
    def test_empty_inputs(self) -> None:
        assert compare_claims([], []) == []

    def test_exact_id_match_repeated(self) -> None:
        baseline = [_claim("c1", confidence=0.8)]
        target = [_claim("c1", confidence=0.9)]
        result = compare_claims(baseline, target)
        assert len(result) == 1
        assert result[0]["status"] == "repeated"
        assert result[0]["confidence_change"] == 0.1

    def test_text_hash_fallback(self) -> None:
        baseline = [_claim("c1", claim_text="AI is transforming work")]
        target = [_claim("c99", claim_text="AI is transforming work")]
        result = compare_claims(baseline, target)
        assert len(result) == 1
        assert result[0]["status"] == "repeated"
        assert result[0]["claim_id"] == "c99"

    def test_text_hash_no_match_different_text(self) -> None:
        baseline = [_claim("c1", claim_text="Claim A")]
        target = [_claim("c2", claim_text="Totally different claim")]
        result = compare_claims(baseline, target)
        statuses = {r["claim_id"]: r["status"] for r in result}
        assert statuses["c2"] == "new"
        assert statuses["c1"] == "disappeared"

    def test_new_claims(self) -> None:
        target = [_claim("c1"), _claim("c2")]
        result = compare_claims([], target)
        assert len(result) == 2
        assert all(r["status"] == "new" for r in result)

    def test_disappeared_claims(self) -> None:
        baseline = [_claim("c1"), _claim("c2")]
        result = compare_claims(baseline, [])
        assert len(result) == 2
        assert all(r["status"] == "disappeared" for r in result)

    def test_confidence_change_positive(self) -> None:
        result = compare_claims([_claim("c1", confidence=0.5)], [_claim("c1", confidence=0.8)])
        assert result[0]["confidence_change"] == 0.3

    def test_confidence_change_negative(self) -> None:
        result = compare_claims([_claim("c1", confidence=0.9)], [_claim("c1", confidence=0.6)])
        assert result[0]["confidence_change"] == -0.3

    def test_confidence_change_zero(self) -> None:
        result = compare_claims([_claim("c1", confidence=0.7)], [_claim("c1", confidence=0.7)])
        assert result[0]["confidence_change"] == 0.0

    def test_corroboration_changed_detected(self) -> None:
        baseline = [_claim("c1", corroboration_status="pending")]
        target = [_claim("c1", corroboration_status="confirmed")]
        result = compare_claims(baseline, target)
        assert result[0]["corroboration_changed"] is True
        assert result[0]["baseline_corroboration"] == "pending"
        assert result[0]["target_corroboration"] == "confirmed"

    def test_corroboration_unchanged(self) -> None:
        baseline = [_claim("c1", corroboration_status="supported")]
        target = [_claim("c1", corroboration_status="supported")]
        result = compare_claims(baseline, target)
        assert result[0]["corroboration_changed"] is False

    def test_review_status_changed(self) -> None:
        baseline = [_claim("c1", needs_review=0)]
        target = [_claim("c1", needs_review=1)]
        result = compare_claims(baseline, target)
        assert result[0]["review_status_changed"] is True

    def test_empty_claim_text_handled(self) -> None:
        baseline = [_claim("c1", claim_text="")]
        target = [_claim("c1", claim_text="")]
        result = compare_claims(baseline, target)
        assert result[0]["status"] == "repeated"

    def test_none_claim_text_handled(self) -> None:
        baseline = [{"claim_id": "c1", "claim_text": None, "confidence": 0.5,
                     "corroboration_status": "x", "needs_review": 0,
                     "claim_type": "fact", "source_url": ""}]
        target = [{"claim_id": "c2", "claim_text": None, "confidence": 0.5,
                   "corroboration_status": "x", "needs_review": 0,
                   "claim_type": "fact", "source_url": ""}]
        result = compare_claims(baseline, target)
        assert len(result) == 2

    def test_ordering_new_repeated_disappeared(self) -> None:
        baseline = [_claim("c1"), _claim("c2", claim_text="unique b")]
        target = [_claim("c1"), _claim("c3", claim_text="unique c")]
        result = compare_claims(baseline, target)
        statuses = [r["status"] for r in result]
        assert statuses == ["new", "repeated", "disappeared"]
