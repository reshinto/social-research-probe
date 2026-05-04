"""Unit tests for claim ledger type definitions and config."""

from __future__ import annotations

import json

from social_research_probe.config import DEFAULT_CONFIG
from social_research_probe.utils.claims.types import ClaimType, ExtractedClaim
from social_research_probe.utils.core.types import (
    ClaimsConfig,
    ExportConfig,
    ScoredItem,
    YouTubePlatformConfig,
)


class TestClaimTypeImport:
    def test_claim_type_literal_values(self) -> None:
        expected = {
            "fact_claim",
            "opinion",
            "prediction",
            "recommendation",
            "experience",
            "question",
            "objection",
            "pain_point",
            "market_signal",
        }
        assert expected == set(ClaimType.__args__)  # type: ignore[attr-defined]


class TestExtractedClaimTypedDict:
    def test_create_with_all_fields(self) -> None:
        claim: ExtractedClaim = {
            "claim_id": "abc123",
            "source_id": "vid_001",
            "source_url": "https://youtube.com/watch?v=vid_001",
            "source_title": "Test Video",
            "claim_text": "AI will replace 50% of jobs by 2030.",
            "evidence_text": "According to recent studies, AI will replace 50% of jobs by 2030.",
            "claim_type": "prediction",
            "entities": ["AI", "50%", "2030"],
            "confidence": 0.7,
            "evidence_layer": "transcript",
            "evidence_tier": "metadata_comments_transcript",
            "needs_corroboration": True,
            "corroboration_status": "pending",
            "contradiction_status": "none",
            "needs_review": False,
            "uncertainty": "low",
            "extraction_method": "deterministic",
            "source_sentence": "AI will replace 50% of jobs by 2030.",
            "position_in_text": 142,
            "context_before": "studies suggest that ",
            "context_after": " This has implications",
            "extracted_at": "2026-05-03T00:00:00+00:00",
        }
        assert claim["claim_type"] == "prediction"
        assert claim["needs_corroboration"] is True
        assert len(claim) == 22

    def test_json_serializable(self) -> None:
        claim: ExtractedClaim = {
            "claim_id": "x",
            "source_id": "s",
            "source_url": "u",
            "source_title": "t",
            "claim_text": "text",
            "evidence_text": "ev",
            "claim_type": "opinion",
            "entities": [],
            "confidence": 0.5,
            "evidence_layer": "title",
            "evidence_tier": "metadata_only",
            "needs_corroboration": False,
            "corroboration_status": "pending",
            "contradiction_status": "none",
            "needs_review": False,
            "uncertainty": "none",
            "extraction_method": "deterministic",
            "source_sentence": "text",
            "position_in_text": 0,
            "context_before": "",
            "context_after": "",
            "extracted_at": "2026-01-01T00:00:00Z",
        }
        serialized = json.dumps(claim)
        restored = json.loads(serialized)
        assert restored == claim


class TestScoredItemAcceptsExtractedClaims:
    def test_scored_item_with_extracted_claims(self) -> None:
        item: ScoredItem = {
            "title": "Test",
            "extracted_claims": [
                {
                    "claim_id": "c1",
                    "source_id": "s1",
                    "source_url": "u",
                    "source_title": "t",
                    "claim_text": "claim",
                    "evidence_text": "ev",
                    "claim_type": "fact_claim",
                    "entities": ["X"],
                    "confidence": 0.7,
                    "evidence_layer": "transcript",
                    "evidence_tier": "full",
                    "needs_corroboration": True,
                    "corroboration_status": "pending",
                    "contradiction_status": "none",
                    "needs_review": False,
                    "uncertainty": "low",
                    "extraction_method": "deterministic",
                    "source_sentence": "claim",
                    "position_in_text": 0,
                    "context_before": "",
                    "context_after": "",
                    "extracted_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
        assert len(item["extracted_claims"]) == 1

    def test_scored_item_without_extracted_claims(self) -> None:
        item: ScoredItem = {"title": "No claims"}
        assert "extracted_claims" not in item


class TestClaimsConfigTypedDict:
    def test_claims_config_fields(self) -> None:
        cfg: ClaimsConfig = {
            "enabled": True,
            "max_claims_per_source": 10,
            "use_llm": False,
            "max_claim_chars": 500,
        }
        assert cfg["enabled"] is True
        assert cfg["max_claims_per_source"] == 10
        assert cfg["use_llm"] is False
        assert cfg["max_claim_chars"] == 500


class TestYouTubePlatformConfigAcceptsClaims:
    def test_platform_config_with_claims(self) -> None:
        cfg: YouTubePlatformConfig = {
            "claims": {"enabled": True, "max_claims_per_source": 5},
        }
        assert cfg["claims"]["enabled"] is True


class TestExportConfigAcceptsClaimsCsv:
    def test_export_config_with_claims_csv(self) -> None:
        cfg: ExportConfig = {"claims_csv": True}
        assert cfg["claims_csv"] is True


class TestDefaultConfigContainsClaimsKeys:
    def test_platforms_youtube_claims_present(self) -> None:
        claims_cfg = DEFAULT_CONFIG["platforms"]["youtube"]["claims"]
        assert claims_cfg["enabled"] is True
        assert claims_cfg["max_claims_per_source"] == 10
        assert claims_cfg["use_llm"] is False
        assert claims_cfg["max_claim_chars"] == 500

    def test_stages_youtube_claims_present(self) -> None:
        assert DEFAULT_CONFIG["stages"]["youtube"]["claims"] is True

    def test_services_youtube_enriching_claims_present(self) -> None:
        enriching = DEFAULT_CONFIG["services"]["youtube"]["enriching"]
        assert enriching["claims"] is True

    def test_platforms_youtube_export_claims_csv_present(self) -> None:
        export_cfg = DEFAULT_CONFIG["platforms"]["youtube"]["export"]
        assert export_cfg["claims_csv"] is True
