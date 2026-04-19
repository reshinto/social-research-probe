"""Tests for social_research_probe.validation.claims.

What is verified here:
    - A sentence containing a number is extracted as a Claim.
    - Sentences shorter than 5 words are not returned.
    - Multiple claims receive consecutive 0-based indices (0, 1, 2, ...).
    - When source_text is not provided it defaults to the full input text.
    - An explicit source_text override is stored on every returned Claim.
    - An empty input string returns an empty list.
"""
from __future__ import annotations

from social_research_probe.validation.claims import extract_claims


def test_extract_claims_basic() -> None:
    """A sentence containing a number is extracted as a Claim."""
    text = "The Eiffel Tower was completed in 1889 and stands 330 metres tall."
    claims = extract_claims(text)
    assert len(claims) == 1
    assert "1889" in claims[0].text


def test_extract_claims_short_sentences_filtered() -> None:
    """Sentences under 5 words are excluded from results."""
    text = "Short. Also short here. The Eiffel Tower was built in 1889 by Gustave Eiffel."
    claims = extract_claims(text)
    # Only the long sentence with a number/proper-noun should pass.
    assert all(len(c.text.split()) >= 5 for c in claims)
    assert any("1889" in c.text for c in claims)


def test_extract_claims_index_increments() -> None:
    """Multiple claims are numbered with consecutive 0-based indices."""
    text = (
        "NASA launched the Hubble Space Telescope in 1990. "
        "The James Webb Space Telescope launched in 2021. "
        "Both telescopes orbit above Earth's atmosphere."
    )
    claims = extract_claims(text)
    assert len(claims) >= 2
    for expected_idx, claim in enumerate(claims):
        assert claim.index == expected_idx, (
            f"Expected index {expected_idx}, got {claim.index}"
        )


def test_extract_claims_source_text_default() -> None:
    """source_text defaults to the full input text when not provided."""
    text = "Marie Curie won the Nobel Prize in Chemistry in 1911."
    claims = extract_claims(text)
    assert claims, "Expected at least one claim"
    for claim in claims:
        assert claim.source_text == text


def test_extract_claims_source_text_override() -> None:
    """An explicit source_text is stored on every returned Claim."""
    text = "Apollo 11 landed on the Moon in July 1969."
    custom_source = "Wikipedia: Moon landing"
    claims = extract_claims(text, source_text=custom_source)
    assert claims, "Expected at least one claim"
    for claim in claims:
        assert claim.source_text == custom_source


def test_empty_text_returns_empty_list() -> None:
    """An empty or whitespace-only input returns an empty list."""
    assert extract_claims("") == []
    assert extract_claims("   ") == []
