"""Unit tests for ClaimExtractionService in services/enriching/claims.py."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.services.enriching.claims import ClaimExtractionService


def _run(coro):
    return asyncio.run(coro)


def _svc() -> ClaimExtractionService:
    return ClaimExtractionService()


def _sample_claim() -> dict:
    return {
        "claim_id": "abc123abc123abcd",
        "source_id": "vid1",
        "source_url": "https://youtube.com/watch?v=vid1",
        "source_title": "Test",
        "claim_text": "AI will replace jobs.",
        "evidence_text": "AI will replace jobs.",
        "claim_type": "prediction",
        "entities": [],
        "confidence": 0.7,
        "evidence_layer": "transcript",
        "evidence_tier": "metadata_transcript",
        "needs_corroboration": True,
        "corroboration_status": "pending",
        "contradiction_status": "none",
        "needs_review": False,
        "uncertainty": "low",
        "extraction_method": "deterministic",
        "source_sentence": "AI will replace jobs.",
        "position_in_text": 0,
        "context_before": "",
        "context_after": "",
        "extracted_at": "2026-01-01T00:00:00+00:00",
    }


def _result_with_claims(claims: list) -> ServiceResult:
    return ServiceResult(
        service_name=ClaimExtractionService.service_name,
        input_key="",
        tech_results=[
            TechResult(
                tech_name="claim_extractor",
                input={},
                output=claims,
                success=True,
            )
        ],
    )


def _result_with_failure() -> ServiceResult:
    return ServiceResult(
        service_name=ClaimExtractionService.service_name,
        input_key="",
        tech_results=[
            TechResult(
                tech_name="claim_extractor",
                input={},
                output=None,
                success=False,
            )
        ],
    )


def _empty_result() -> ServiceResult:
    return ServiceResult(
        service_name=ClaimExtractionService.service_name,
        input_key="",
        tech_results=[],
    )


class TestClaimExtractionServiceMeta:
    def test_service_name(self) -> None:
        assert ClaimExtractionService.service_name == "youtube.enriching.claims"

    def test_enabled_config_key(self) -> None:
        assert ClaimExtractionService.enabled_config_key == "services.youtube.enriching.claims"


class TestClaimExtractionServiceTechnologies:
    def test_get_technologies_returns_claim_extraction_tech(self) -> None:
        from social_research_probe.technologies.claims import ClaimExtractionTech

        techs = _svc()._get_technologies()
        assert len(techs) == 1
        assert isinstance(techs[0], ClaimExtractionTech)


class TestClaimExtractionServiceExecuteService:
    def test_merges_extracted_claims_into_item(self) -> None:
        claims = [_sample_claim()]
        data = {"title": "Test", "id": "vid1"}
        result = _run(_svc().execute_service(data, _result_with_claims(claims)))
        output = result.tech_results[0].output
        assert isinstance(output, dict)
        assert output["extracted_claims"] == claims

    def test_preserves_existing_item_fields(self) -> None:
        data = {"title": "Test", "id": "vid1", "score": 0.9}
        result = _run(_svc().execute_service(data, _result_with_claims([])))
        output = result.tech_results[0].output
        assert output["title"] == "Test"
        assert output["score"] == 0.9

    def test_handles_empty_claims(self) -> None:
        data = {"title": "No claimable text."}
        result = _run(_svc().execute_service(data, _result_with_claims([])))
        output = result.tech_results[0].output
        assert output["extracted_claims"] == []

    def test_tech_failure_gives_empty_claims(self) -> None:
        data = {"title": "Test"}
        result = _run(_svc().execute_service(data, _result_with_failure()))
        output = result.tech_results[0].output
        assert isinstance(output, dict)
        assert output["extracted_claims"] == []

    def test_no_tech_results_still_merges(self) -> None:
        data = {"title": "Test"}
        result = _run(_svc().execute_service(data, _empty_result()))
        assert result.tech_results == []

    def test_non_dict_input_returns_result_unchanged(self) -> None:
        result = _run(_svc().execute_service("not-a-dict", _empty_result()))
        assert result.tech_results == []

    def test_non_dict_input_with_tech_results_unchanged(self) -> None:
        result = _run(_svc().execute_service(42, _result_with_claims([])))
        assert result.tech_results[0].output == []

    def test_service_disabled_returns_empty_tech_results(self) -> None:
        with patch.object(ClaimExtractionService, "is_enabled", return_value=False):
            result = _run(_svc().execute_one({"title": "Test"}))
        assert result.tech_results == []
        assert result.service_name == ClaimExtractionService.service_name
