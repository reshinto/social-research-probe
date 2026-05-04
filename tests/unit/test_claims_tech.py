"""Unit tests for ClaimExtractionTech in technologies/claims/__init__.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from social_research_probe.technologies.claims import (
    ClaimExtractionTech,
    _pick_source_meta,
    _pick_text,
)


def _mock_cfg(max_claims: int = 10, max_chars: int = 500, use_llm: bool = False) -> MagicMock:
    cfg = MagicMock()
    cfg.raw = {
        "platforms": {
            "youtube": {
                "claims": {
                    "max_claims_per_source": max_claims,
                    "max_claim_chars": max_chars,
                    "use_llm": use_llm,
                }
            }
        }
    }
    return cfg


def _run_execute(data: dict, max_claims: int = 10, max_chars: int = 500) -> list:
    with patch(
        "social_research_probe.technologies.claims.load_active_config",
        return_value=_mock_cfg(max_claims=max_claims, max_chars=max_chars),
    ):
        return asyncio.run(ClaimExtractionTech()._execute(data))


class TestClaimExtractionTechMeta:
    def test_name(self) -> None:
        assert ClaimExtractionTech.name == "claim_extractor"

    def test_enabled_config_key(self) -> None:
        assert ClaimExtractionTech.enabled_config_key == "claim_extractor"


class TestPickText:
    def test_prefers_text_surrogate_primary_text(self) -> None:
        data = {
            "text_surrogate": {
                "primary_text": "surrogate text",
                "primary_text_source": "transcript",
            },
            "transcript": "fallback transcript",
        }
        text, layer = _pick_text(data)
        assert text == "surrogate text"
        assert layer == "transcript"

    def test_falls_back_to_transcript(self) -> None:
        data = {"transcript": "plain transcript"}
        text, layer = _pick_text(data)
        assert text == "plain transcript"
        assert layer == "transcript"

    def test_falls_back_to_summary(self) -> None:
        data = {"summary": "a summary here"}
        text, layer = _pick_text(data)
        assert text == "a summary here"
        assert layer == "summary"

    def test_returns_empty_when_no_text(self) -> None:
        text, layer = _pick_text({"title": "Only title"})
        assert text == ""
        assert layer == "title"

    def test_primary_text_source_defaults_to_title(self) -> None:
        data = {"text_surrogate": {"primary_text": "some text"}}
        _text, layer = _pick_text(data)
        assert layer == "title"


class TestPickSourceMeta:
    def test_reads_source_id_from_surrogate(self) -> None:
        data = {"text_surrogate": {"source_id": "sid1"}, "id": "fallback"}
        source_id, _url, _title, _tier = _pick_source_meta(data)
        assert source_id == "sid1"

    def test_falls_back_source_id_to_item_id(self) -> None:
        data = {"id": "item_id"}
        source_id, _url, _title, _tier = _pick_source_meta(data)
        assert source_id == "item_id"

    def test_reads_evidence_tier_from_surrogate(self) -> None:
        data = {"text_surrogate": {"evidence_tier": "metadata_transcript"}}
        _sid, _url, _title, tier = _pick_source_meta(data)
        assert tier == "metadata_transcript"

    def test_evidence_tier_defaults_to_metadata_only(self) -> None:
        _sid, _url, _title, tier = _pick_source_meta({})
        assert tier == "metadata_only"


class TestClaimExtractionTechExecute:
    def test_extracts_from_text_surrogate_primary_text(self) -> None:
        data = {
            "text_surrogate": {
                "primary_text": "AI will replace 50% of jobs.",
                "primary_text_source": "transcript",
                "source_id": "vid1",
                "evidence_tier": "metadata_transcript",
            },
            "url": "https://youtube.com/watch?v=vid1",
            "title": "Test",
        }
        result = _run_execute(data)
        assert len(result) >= 1
        assert result[0]["claim_type"] == "prediction"
        assert result[0]["evidence_layer"] == "transcript"

    def test_fallback_to_transcript(self) -> None:
        data = {
            "transcript": "Revenue grew by 42% last year.",
            "url": "https://youtube.com/watch?v=vid1",
            "title": "Test",
        }
        result = _run_execute(data)
        assert len(result) >= 1
        assert result[0]["evidence_layer"] == "transcript"

    def test_fallback_to_summary(self) -> None:
        data = {
            "summary": "I think this approach is wrong.",
            "url": "https://youtube.com/watch?v=vid1",
            "title": "Test",
        }
        result = _run_execute(data)
        assert len(result) >= 1
        assert result[0]["evidence_layer"] == "summary"

    def test_returns_empty_for_no_text(self) -> None:
        data = {"title": "No content", "url": "https://youtube.com/watch?v=vid1"}
        result = _run_execute(data)
        assert result == []

    def test_respects_max_claims_per_source(self) -> None:
        sentences = " ".join([f"AI will replace {i} jobs." for i in range(20)])
        data = {"transcript": sentences, "url": "u", "title": "T"}
        result = _run_execute(data, max_claims=2)
        assert len(result) <= 2

    def test_respects_max_claim_chars(self) -> None:
        long_sentence = "According to experts, " + "a" * 600 + "."
        data = {"transcript": f"{long_sentence} AI will grow.", "url": "u", "title": "T"}
        result = _run_execute(data, max_chars=50)
        assert all(len(c["claim_text"]) <= 50 for c in result)

    def test_use_llm_true_returns_llm_claims_on_success(self) -> None:
        llm_claim = {
            "claim_id": "abc",
            "source_id": "s",
            "source_url": "u",
            "source_title": "T",
            "claim_text": "Revenue grew by 50%.",
            "evidence_text": "Revenue grew by 50%.",
            "claim_type": "fact_claim",
            "entities": ["50%"],
            "confidence": 0.9,
            "evidence_layer": "transcript",
            "evidence_tier": "metadata_comments_transcript",
            "needs_corroboration": True,
            "corroboration_status": "pending",
            "contradiction_status": "none",
            "needs_review": False,
            "uncertainty": "low",
            "extraction_method": "llm",
            "source_sentence": "Revenue grew by 50%.",
            "position_in_text": 0,
            "context_before": "",
            "context_after": "",
            "extracted_at": "2026-01-01T00:00:00+00:00",
        }
        data = {"transcript": "Revenue grew by 50%.", "url": "u", "title": "T"}
        with (
            patch(
                "social_research_probe.technologies.claims.load_active_config",
                return_value=_mock_cfg(use_llm=True),
            ),
            patch(
                "social_research_probe.utils.claims.llm_extractor.extract_claims_llm",
                new=AsyncMock(return_value=[llm_claim]),
            ),
        ):
            result = asyncio.run(ClaimExtractionTech()._execute(data))
        assert len(result) == 1
        assert result[0]["extraction_method"] == "llm"

    def test_use_llm_true_falls_back_to_deterministic_on_llm_failure(self) -> None:
        data = {"transcript": "Revenue grew by 50%.", "url": "u", "title": "T"}
        with (
            patch(
                "social_research_probe.technologies.claims.load_active_config",
                return_value=_mock_cfg(use_llm=True),
            ),
            patch(
                "social_research_probe.utils.claims.llm_extractor.extract_claims_llm",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = asyncio.run(ClaimExtractionTech()._execute(data))
        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)
