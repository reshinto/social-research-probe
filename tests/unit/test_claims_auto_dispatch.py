"""Unit tests for extract_claims_auto dispatcher."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from social_research_probe.utils.claims.extractor import extract_claims_auto

_BASE = {
    "source_id": "vid001",
    "source_url": "https://youtube.com/watch?v=vid001",
    "source_title": "Test",
    "evidence_layer": "transcript",
    "evidence_tier": "metadata_comments_transcript",
}

_DETERMINISTIC_TEXT = "Revenue grew by 42% last year."
_LLM_CLAIM = {
    "claim_id": "abc123",
    "source_id": "vid001",
    "source_url": "https://youtube.com/watch?v=vid001",
    "source_title": "Test",
    "claim_text": "Revenue grew by 42% last year.",
    "evidence_text": "Revenue grew by 42% last year.",
    "claim_type": "fact_claim",
    "entities": ["42%"],
    "confidence": 0.9,
    "evidence_layer": "transcript",
    "evidence_tier": "metadata_comments_transcript",
    "needs_corroboration": True,
    "corroboration_status": "pending",
    "contradiction_status": "none",
    "needs_review": False,
    "uncertainty": "low",
    "extraction_method": "llm",
    "source_sentence": "Revenue grew by 42% last year.",
    "position_in_text": 0,
    "context_before": "",
    "context_after": "",
    "extracted_at": "2026-01-01T00:00:00+00:00",
}


def _run(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


class TestExtractClaimsAutoUseLlmFalse:
    def test_deterministic_called_returns_claims(self) -> None:
        result = _run(extract_claims_auto(_DETERMINISTIC_TEXT, **_BASE, use_llm=False))
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)

    def test_llm_extractor_not_imported_when_use_llm_false(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor.extract_claims_llm"
        ) as mock_llm:
            _run(extract_claims_auto(_DETERMINISTIC_TEXT, **_BASE, use_llm=False))
        mock_llm.assert_not_called()

    def test_empty_text_returns_empty(self) -> None:
        result = _run(extract_claims_auto("", **_BASE, use_llm=False))
        assert result == []


class TestExtractClaimsAutoUseLlmTrue:
    def test_llm_success_returns_llm_claims(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor.extract_claims_llm",
            new=AsyncMock(return_value=[_LLM_CLAIM]),
        ):
            result = _run(extract_claims_auto(_DETERMINISTIC_TEXT, **_BASE, use_llm=True))
        assert result == [_LLM_CLAIM]
        assert result[0]["extraction_method"] == "llm"

    def test_llm_returns_none_falls_back_to_deterministic(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor.extract_claims_llm",
            new=AsyncMock(return_value=None),
        ):
            result = _run(extract_claims_auto(_DETERMINISTIC_TEXT, **_BASE, use_llm=True))
        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)

    def test_llm_returns_empty_list_falls_back_to_deterministic(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor.extract_claims_llm",
            new=AsyncMock(return_value=[]),
        ):
            result = _run(extract_claims_auto(_DETERMINISTIC_TEXT, **_BASE, use_llm=True))
        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)

    def test_llm_raises_falls_back_to_deterministic(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor.extract_claims_llm",
            new=AsyncMock(side_effect=RuntimeError("LLM crashed")),
        ):
            result = _run(extract_claims_auto(_DETERMINISTIC_TEXT, **_BASE, use_llm=True))
        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)

    def test_empty_text_returns_empty_regardless(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor.extract_claims_llm",
            new=AsyncMock(return_value=[_LLM_CLAIM]),
        ):
            result = _run(extract_claims_auto("", **_BASE, use_llm=True))
        assert result == []
