"""Tests for tech.validation: ai_slop_detector + claim_extractor."""

from __future__ import annotations

from social_research_probe.technologies.validation.ai_slop_detector import score
from social_research_probe.technologies.validation.claim_extractor import (
    Claim,
    extract_claims,
)


class TestAiSlopScore:
    def test_empty(self):
        assert score("") == 0.0
        assert score("   ") == 0.0

    def test_in_range(self):
        out = score("This is a fine sentence about machine learning models.")
        assert 0.0 <= out <= 1.0

    def test_boilerplate_increases(self):
        clean = score("Models perform inference. Results vary across datasets.")
        bad = "In conclusion, it is important to note that as an AI I cannot. Of course, certainly."
        assert score(bad) > clean


class TestExtractClaims:
    def test_empty(self):
        assert extract_claims("") == []
        assert extract_claims("   ") == []

    def test_yields_candidates_with_numbers(self):
        text = "OpenAI launched GPT-4 in 2023. The model has billions of parameters."
        claims = extract_claims(text)
        assert claims
        assert all(isinstance(c, Claim) for c in claims)

    def test_short_sentence_filtered(self):
        text = "Hi there. OpenAI launched GPT-4 in 2023 to wide acclaim."
        claims = extract_claims(text)
        assert all(len(c.text.split()) >= 5 for c in claims)

    def test_resolves_source_url(self):
        text = "OpenAI launched GPT-4 in 2023 to wide acclaim."
        claims = extract_claims(text, source_url="https://x.com")
        assert claims[0].source_url == "https://x.com"

    def test_explicit_source_text_used(self):
        text = "OpenAI launched GPT-4 in 2023 to wide acclaim."
        claims = extract_claims(text, source_text="orig")
        assert claims[0].source_text == "orig"
