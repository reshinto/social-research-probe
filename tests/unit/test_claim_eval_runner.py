"""Tests for claim quality assessment runner and gates."""

from __future__ import annotations

from social_research_probe.utils.claims import extractor
from tests.evals.assess_claims_quality import _GATES, main, run_assessment
from tests.evals.claim_fixtures import ClaimEvalCase


class TestRunAssessment:
    def test_default_cases_pass(self):
        result = run_assessment()
        assert result["passed"] is True

    def test_with_default_cases_returns_dict(self):
        result = run_assessment()
        assert "passed" in result
        assert "gates" in result
        assert "aggregate" in result
        assert "per_case" in result
        assert "total_claims" in result
        assert isinstance(result["passed"], bool)

    def test_custom_cases_override(self):
        custom = [
            ClaimEvalCase(
                case_id="custom1",
                input_text="Python is great for data science. It has many libraries.",
                source_id="s1",
                source_title="Test",
                evidence_layer="transcript",
                evidence_tier="metadata_transcript",
                expected_claim_types=["opinion"],
                should_extract_phrases=["Python"],
                should_not_extract_phrases=[],
                minimum_claim_count=1,
                maximum_claim_count=5,
                notes="custom",
            )
        ]
        result = run_assessment(cases=custom)
        assert len(result["per_case"]) == 1
        assert result["per_case"][0]["case_id"] == "custom1"

    def test_empty_case_produces_zero_claims(self):
        empty = [
            ClaimEvalCase(
                case_id="empty",
                input_text="",
                source_id="s1",
                source_title="Empty",
                evidence_layer="transcript",
                evidence_tier="metadata_only",
                expected_claim_types=[],
                should_extract_phrases=[],
                should_not_extract_phrases=[],
                minimum_claim_count=0,
                maximum_claim_count=0,
                notes="empty",
            )
        ]
        result = run_assessment(cases=empty)
        assert result["per_case"][0]["claim_count"] == 0
        assert result["total_claims"] == 0

    def test_per_case_has_all_metrics(self):
        result = run_assessment()
        for case_result in result["per_case"]:
            assert "case_id" in case_result
            assert "claim_count" in case_result
            assert "valid_claim_rate" in case_result
            assert "expected_type_coverage" in case_result
            assert "should_extract_coverage" in case_result
            assert "should_not_extract_violation_rate" in case_result
            assert "duplicate_claim_rate" in case_result
            assert "grounded_claim_rate" in case_result
            assert "needs_review_rate" in case_result
            assert "hallucination_risk_rate" in case_result
            assert "count_in_range" in case_result


class TestGates:
    def test_grounded_gate_fails_when_grounding_degraded(self, monkeypatch):
        original = extractor.extract_claims_deterministic

        def degraded_grounding(*args, **kwargs):
            claims = original(*args, **kwargs)
            return [{**claim, "position_in_text": 0} for claim in claims]

        monkeypatch.setattr(extractor, "extract_claims_deterministic", degraded_grounding)

        result = run_assessment()

        gate = result["gates"]["grounded_claim_rate"]
        assert gate["actual"] < gate["threshold"]
        assert gate["passed"] is False
        assert result["passed"] is False

    def test_gate_failure_detected(self):
        bad_case = ClaimEvalCase(
            case_id="bad",
            input_text="subscribe like comment share bell icon notification",
            source_id="s1",
            source_title="Bad",
            evidence_layer="transcript",
            evidence_tier="metadata_transcript",
            expected_claim_types=["fact_claim", "opinion", "prediction"],
            should_extract_phrases=["quantum computing", "neural networks"],
            should_not_extract_phrases=["subscribe", "bell icon"],
            minimum_claim_count=0,
            maximum_claim_count=0,
            notes="designed to fail gates",
        )
        result = run_assessment(cases=[bad_case])
        if result["total_claims"] > 0:
            failed_gates = [k for k, v in result["gates"].items() if not v["passed"]]
            assert len(failed_gates) > 0

    def test_all_gates_have_thresholds(self):
        result = run_assessment()
        for gate_name, gate_info in result["gates"].items():
            assert "threshold" in gate_info
            assert "actual" in gate_info
            assert "passed" in gate_info
            assert gate_name in _GATES


class TestMain:
    def test_default_cases_return_zero(self):
        assert main() == 0

    def test_returns_int(self):
        result = main()
        assert result in (0, 1)
