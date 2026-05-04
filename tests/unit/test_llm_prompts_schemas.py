"""Tests for LLM prompt templates and JSON schema constants."""

from __future__ import annotations

from typing import get_args

from social_research_probe.utils.claims.types import ClaimType
from social_research_probe.utils.llm.prompts import (
    CLAIM_EXTRACTION_PROMPT,
    CLASSIFICATION_PROMPT,
    CODEX_SEARCH_PROMPT,
    LLM_SEARCH_CORROBORATION_PROMPT,
    SYNTHESIS_PROMPT,
)
from social_research_probe.utils.llm.schemas import (
    CLAIM_EXTRACTION_SCHEMA,
    NL_QUERY_CLASSIFICATION_SCHEMA,
    PURPOSE_SUGGESTIONS_SCHEMA,
    TOPIC_SUGGESTIONS_SCHEMA,
)


class TestClaimExtractionPrompt:
    def test_has_max_claims_placeholder(self) -> None:
        assert "{max_claims}" in CLAIM_EXTRACTION_PROMPT

    def test_has_source_title_placeholder(self) -> None:
        assert "{source_title}" in CLAIM_EXTRACTION_PROMPT

    def test_has_text_placeholder(self) -> None:
        assert "{text}" in CLAIM_EXTRACTION_PROMPT

    def test_has_max_chars_placeholder(self) -> None:
        assert "{max_chars}" in CLAIM_EXTRACTION_PROMPT

    def test_includes_all_nine_claim_types(self) -> None:
        claim_types = get_args(ClaimType)
        for ct in claim_types:
            assert ct in CLAIM_EXTRACTION_PROMPT, f"Missing claim type: {ct}"

    def test_instructs_json_only(self) -> None:
        lower = CLAIM_EXTRACTION_PROMPT.lower()
        assert "json only" in lower

    def test_instructs_not_to_invent_facts(self) -> None:
        lower = CLAIM_EXTRACTION_PROMPT.lower()
        assert "do not invent" in lower

    def test_instructs_use_only_supplied_text(self) -> None:
        lower = CLAIM_EXTRACTION_PROMPT.lower()
        assert "supported by the provided text" in lower or "stated in" in lower

    def test_renders_without_error(self) -> None:
        rendered = CLAIM_EXTRACTION_PROMPT.format(
            max_claims=10,
            source_title="Test Title",
            text="Some body text.",
            max_chars=500,
        )
        assert "Test Title" in rendered
        assert "Some body text." in rendered


class TestClaimExtractionSchema:
    def test_top_level_has_claims_required(self) -> None:
        assert "claims" in CLAIM_EXTRACTION_SCHEMA["required"]

    def test_claims_is_array(self) -> None:
        claims_prop = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]
        assert claims_prop["type"] == "array"

    def test_claim_type_enum_matches_claim_type_literal(self) -> None:
        claim_types = set(get_args(ClaimType))
        item_props = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]["items"]["properties"]
        schema_enum = set(item_props["claim_type"]["enum"])
        assert schema_enum == claim_types

    def test_item_required_includes_claim_text(self) -> None:
        item = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]["items"]
        assert "claim_text" in item["required"]

    def test_item_required_includes_claim_type(self) -> None:
        item = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]["items"]
        assert "claim_type" in item["required"]

    def test_item_required_includes_confidence(self) -> None:
        item = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]["items"]
        assert "confidence" in item["required"]

    def test_item_has_entities_property(self) -> None:
        item_props = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]["items"]["properties"]
        assert "entities" in item_props

    def test_item_has_needs_corroboration_property(self) -> None:
        item_props = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]["items"]["properties"]
        assert "needs_corroboration" in item_props

    def test_item_has_uncertainty_property(self) -> None:
        item_props = CLAIM_EXTRACTION_SCHEMA["properties"]["claims"]["items"]["properties"]
        assert "uncertainty" in item_props


class TestExistingPromptsUnchanged:
    def test_synthesis_prompt_exists(self) -> None:
        assert "{topic}" in SYNTHESIS_PROMPT
        assert "{platform}" in SYNTHESIS_PROMPT

    def test_corroboration_prompt_exists(self) -> None:
        assert "{claim_text}" in LLM_SEARCH_CORROBORATION_PROMPT

    def test_classification_prompt_exists(self) -> None:
        assert "{query}" in CLASSIFICATION_PROMPT

    def test_codex_search_prompt_exists(self) -> None:
        assert "{query}" in CODEX_SEARCH_PROMPT


class TestExistingSchemasUnchanged:
    def test_topic_suggestions_schema(self) -> None:
        assert "suggestions" in TOPIC_SUGGESTIONS_SCHEMA["required"]

    def test_purpose_suggestions_schema(self) -> None:
        assert "suggestions" in PURPOSE_SUGGESTIONS_SCHEMA["required"]

    def test_nl_query_classification_schema(self) -> None:
        assert "topic" in NL_QUERY_CLASSIFICATION_SCHEMA["required"]
