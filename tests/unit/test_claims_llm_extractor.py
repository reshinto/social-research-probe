"""Unit tests for LLM-backed claim extractor module."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.utils.claims.llm_extractor import (
    _build_claim_extraction_prompt,
    _coerce_claim_type,
    _coerce_confidence,
    _coerce_entities,
    _derive_uncertainty,
    _extract_json_object,
    _normalize_llm_claim,
    _preferred_runner,
    _run_llm,
    extract_claims_llm,
)

_BASE_SOURCE_KWARGS: dict[str, object] = {
    "source_id": "vid001",
    "source_url": "https://youtube.com/watch?v=vid001",
    "source_title": "Test Video",
    "evidence_layer": "transcript",
    "evidence_tier": "metadata_comments_transcript",
    "text": "AI will replace 50% of jobs by 2030.",
    "extracted_at": "2026-01-01T00:00:00+00:00",
    "max_chars": 500,
}

_VALID_RESPONSE: dict[str, object] = {
    "claims": [
        {
            "claim_text": "AI will replace 50% of jobs by 2030.",
            "claim_type": "prediction",
            "confidence": 0.85,
            "entities": ["AI", "50%"],
            "needs_corroboration": True,
            "uncertainty": "low",
        }
    ]
}


class TestBuildPrompt:
    def test_fills_all_placeholders(self) -> None:
        prompt = _build_claim_extraction_prompt("body text", "My Title", 5, 200)
        assert "My Title" in prompt
        assert "body text" in prompt
        assert "5" in prompt
        assert "200" in prompt

    def test_truncates_long_text(self) -> None:
        long = "x" * 10_000
        prompt = _build_claim_extraction_prompt(long, "T", 10, 500)
        assert long not in prompt
        assert "x" * 5_000 in prompt


class TestExtractJsonObject:
    def test_dict_returned_directly(self) -> None:
        d = {"claims": []}
        assert _extract_json_object(d) is d

    def test_valid_json_string_parsed(self) -> None:
        result = _extract_json_object('{"claims": []}')
        assert result == {"claims": []}

    def test_invalid_json_string_returns_none(self) -> None:
        assert _extract_json_object("not json") is None

    def test_json_list_returns_none(self) -> None:
        assert _extract_json_object("[1, 2, 3]") is None

    def test_non_string_non_dict_returns_none(self) -> None:
        assert _extract_json_object(42) is None
        assert _extract_json_object(None) is None


class TestCoerceClaimType:
    def test_valid_type_returned(self) -> None:
        assert _coerce_claim_type("prediction") == "prediction"
        assert _coerce_claim_type("fact_claim") == "fact_claim"

    def test_invalid_type_returns_none(self) -> None:
        assert _coerce_claim_type("banana") is None
        assert _coerce_claim_type(None) is None
        assert _coerce_claim_type(42) is None


class TestDeriveUncertainty:
    def test_high_confidence_returns_low(self) -> None:
        assert _derive_uncertainty(0.9) == "low"
        assert _derive_uncertainty(0.8) == "low"

    def test_medium_confidence_returns_medium(self) -> None:
        assert _derive_uncertainty(0.7) == "medium"
        assert _derive_uncertainty(0.5) == "medium"

    def test_low_confidence_returns_high(self) -> None:
        assert _derive_uncertainty(0.4) == "high"
        assert _derive_uncertainty(0.0) == "high"


class TestPreferredRunner:
    def test_returns_llm_runner_from_config(self) -> None:
        mock_cfg = MagicMock()
        mock_cfg.llm_runner = "claude"
        with patch(
            "social_research_probe.config.load_active_config",
            return_value=mock_cfg,
        ):
            result = _preferred_runner()
        assert result == "claude"


class TestRunLlm:
    def test_calls_run_with_fallback(self) -> None:
        with (
            patch(
                "social_research_probe.utils.claims.llm_extractor._preferred_runner",
                return_value="claude",
            ),
            patch(
                "social_research_probe.utils.llm.registry.run_with_fallback",
                return_value={"claims": []},
            ) as mock_run,
        ):
            result = _run_llm("some prompt")
        mock_run.assert_called_once()
        assert result == {"claims": []}


class TestCoerceConfidence:
    def test_valid_float_returned(self) -> None:
        assert _coerce_confidence(0.9) == pytest.approx(0.9)

    def test_clamps_above_one(self) -> None:
        assert _coerce_confidence(1.5) == pytest.approx(1.0)

    def test_clamps_below_zero(self) -> None:
        assert _coerce_confidence(-0.5) == pytest.approx(0.0)

    def test_non_numeric_defaults_to_0_75(self) -> None:
        assert _coerce_confidence("high") == pytest.approx(0.75)
        assert _coerce_confidence(None) == pytest.approx(0.75)

    def test_bool_not_treated_as_numeric(self) -> None:
        assert _coerce_confidence(True) == pytest.approx(0.75)


class TestCoerceEntities:
    def test_valid_list_returned(self) -> None:
        assert _coerce_entities(["Apple", "50%"]) == ["Apple", "50%"]

    def test_non_strings_filtered(self) -> None:
        assert _coerce_entities(["Apple", 42, None, "50%"]) == ["Apple", "50%"]

    def test_non_list_returns_empty(self) -> None:
        assert _coerce_entities("Apple") == []
        assert _coerce_entities(None) == []


class TestNormalizeLlmClaim:
    def test_valid_claim_returns_full_extract(self) -> None:
        raw = {
            "claim_text": "AI will replace 50% of jobs by 2030.",
            "claim_type": "prediction",
            "confidence": 0.85,
            "entities": ["AI", "50%"],
        }
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["claim_type"] == "prediction"
        assert result["extraction_method"] == "llm"
        assert result["confidence"] == pytest.approx(0.85)
        assert result["corroboration_status"] == "pending"
        assert result["contradiction_status"] == "none"

    def test_non_dict_returns_none(self) -> None:
        assert _normalize_llm_claim("not a dict", **_BASE_SOURCE_KWARGS) is None

    def test_missing_claim_text_returns_none(self) -> None:
        assert (
            _normalize_llm_claim(
                {"claim_type": "opinion", "confidence": 0.8}, **_BASE_SOURCE_KWARGS
            )
            is None
        )

    def test_empty_claim_text_returns_none(self) -> None:
        assert (
            _normalize_llm_claim(
                {"claim_text": "   ", "claim_type": "opinion", "confidence": 0.8},
                **_BASE_SOURCE_KWARGS,
            )
            is None
        )

    def test_invalid_claim_type_returns_none(self) -> None:
        raw = {"claim_text": "Something.", "claim_type": "banana", "confidence": 0.8}
        assert _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS) is None

    def test_needs_review_true_when_confidence_below_0_8(self) -> None:
        raw = {"claim_text": "AI will take jobs.", "claim_type": "prediction", "confidence": 0.6}
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["needs_review"] is True

    def test_needs_review_false_when_confidence_at_least_0_8(self) -> None:
        raw = {"claim_text": "AI will take jobs.", "claim_type": "prediction", "confidence": 0.8}
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["needs_review"] is False

    def test_claim_id_deterministic(self) -> None:
        raw = {"claim_text": "AI will take jobs.", "claim_type": "prediction", "confidence": 0.9}
        r1 = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        r2 = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert r1 is not None and r2 is not None
        assert r1["claim_id"] == r2["claim_id"]

    def test_position_in_text_found(self) -> None:
        raw = {
            "claim_text": "AI will replace 50% of jobs by 2030.",
            "claim_type": "prediction",
            "confidence": 0.9,
        }
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["position_in_text"] == 0

    def test_position_in_text_not_found_defaults_to_0(self) -> None:
        raw = {
            "claim_text": "This sentence is not in the source text.",
            "claim_type": "opinion",
            "confidence": 0.9,
        }
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["position_in_text"] == 0

    def test_needs_corroboration_true_for_prediction(self) -> None:
        raw = {"claim_text": "AI will take jobs.", "claim_type": "prediction", "confidence": 0.9}
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["needs_corroboration"] is True

    def test_needs_corroboration_false_for_opinion(self) -> None:
        raw = {"claim_text": "I think this is wrong.", "claim_type": "opinion", "confidence": 0.9}
        kwargs = {**_BASE_SOURCE_KWARGS, "text": "I think this is wrong."}
        result = _normalize_llm_claim(raw, **kwargs)
        assert result is not None
        assert result["needs_corroboration"] is False

    def test_llm_bool_overrides_needs_corroboration(self) -> None:
        raw = {
            "claim_text": "AI will take jobs.",
            "claim_type": "prediction",
            "confidence": 0.9,
            "needs_corroboration": False,
        }
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["needs_corroboration"] is False

    def test_entities_non_strings_filtered(self) -> None:
        raw = {
            "claim_text": "AI will take jobs.",
            "claim_type": "prediction",
            "confidence": 0.9,
            "entities": ["AI", 42, None],
        }
        result = _normalize_llm_claim(raw, **_BASE_SOURCE_KWARGS)
        assert result is not None
        assert result["entities"] == ["AI"]

    def test_claim_text_truncated_to_max_chars(self) -> None:
        long_text = "a" * 600
        raw = {"claim_text": long_text, "claim_type": "opinion", "confidence": 0.9}
        kwargs = {**_BASE_SOURCE_KWARGS, "max_chars": 50}
        result = _normalize_llm_claim(raw, **kwargs)
        assert result is not None
        assert len(result["claim_text"]) == 50


class TestExtractClaimsLlm:
    def _run(self, coro: object) -> object:
        return asyncio.run(coro)

    def _base_kwargs(self) -> dict[str, object]:
        return {
            "source_id": "vid001",
            "source_url": "https://youtube.com/watch?v=vid001",
            "source_title": "Test Video",
            "evidence_layer": "transcript",
            "evidence_tier": "metadata_comments_transcript",
        }

    def test_valid_response_returns_claims(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            return_value=_VALID_RESPONSE,
        ):
            result = self._run(
                extract_claims_llm("AI will replace 50% of jobs by 2030.", **self._base_kwargs())
            )
        assert result is not None
        assert len(result) == 1
        assert result[0]["extraction_method"] == "llm"

    def test_run_llm_exception_returns_none(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            side_effect=RuntimeError("LLM down"),
        ):
            result = self._run(extract_claims_llm("AI will replace jobs.", **self._base_kwargs()))
        assert result is None

    def test_response_not_dict_returns_none(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            return_value=[{"claim_text": "Something.", "claim_type": "opinion"}],
        ):
            result = self._run(extract_claims_llm("Something.", **self._base_kwargs()))
        assert result is None

    def test_missing_claims_key_returns_none(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            return_value={"bad": "data"},
        ):
            result = self._run(extract_claims_llm("Something.", **self._base_kwargs()))
        assert result is None

    def test_claims_not_list_returns_none(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            return_value={"claims": "not a list"},
        ):
            result = self._run(extract_claims_llm("Something.", **self._base_kwargs()))
        assert result is None

    def test_all_claims_invalid_returns_none(self) -> None:
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            return_value={"claims": [{"claim_type": "banana"}]},
        ):
            result = self._run(extract_claims_llm("Something.", **self._base_kwargs()))
        assert result is None

    def test_duplicate_claims_deduplicated(self) -> None:
        duplicate_response = {
            "claims": [
                {
                    "claim_text": "AI will take jobs.",
                    "claim_type": "prediction",
                    "confidence": 0.9,
                },
                {
                    "claim_text": "AI will take jobs.",
                    "claim_type": "prediction",
                    "confidence": 0.9,
                },
            ]
        }
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            return_value=duplicate_response,
        ):
            result = self._run(extract_claims_llm("AI will take jobs.", **self._base_kwargs()))
        assert result is not None
        assert len(result) == 1

    def test_max_claims_enforced(self) -> None:
        many_response = {
            "claims": [
                {
                    "claim_text": f"Claim number {i} is true.",
                    "claim_type": "opinion",
                    "confidence": 0.9,
                }
                for i in range(10)
            ]
        }
        with patch(
            "social_research_probe.utils.claims.llm_extractor._run_llm",
            return_value=many_response,
        ):
            result = self._run(
                extract_claims_llm(
                    " ".join(f"Claim number {i} is true." for i in range(10)),
                    **self._base_kwargs(),
                    max_claims=3,
                )
            )
        assert result is not None
        assert len(result) == 3

    def test_empty_text_returns_none(self) -> None:
        result = self._run(extract_claims_llm("", **self._base_kwargs()))
        assert result is None

    def test_whitespace_only_returns_none(self) -> None:
        result = self._run(extract_claims_llm("   ", **self._base_kwargs()))
        assert result is None
