"""Tests for social_research_probe.validation.ai_slop.

What is verified here:
    - Normal prose produces a low slop score (below 0.3).
    - Text dense with known boilerplate phrases drives the score above 0.5.
    - Text containing repeated trigrams produces an above-baseline score (> 0.3).
    - The score is always clamped to the unit interval [0, 1].
    - An empty string returns exactly 0.0.
"""

from __future__ import annotations

from social_research_probe.validation.ai_slop import score


def test_clean_text_low_score() -> None:
    """Normal, varied prose should score below 0.3."""
    text = (
        "The researchers observed that solar panels installed on south-facing "
        "rooftops in temperate climates generated 23 percent more electricity "
        "during summer months than their north-facing counterparts. "
        "Additional monitoring data collected over five years confirmed the trend."
    )
    result = score(text)
    assert result < 0.3, f"Expected score < 0.3 for clean prose, got {result}"


def test_boilerplate_phrases_increase_score() -> None:
    """Text loaded with boilerplate phrases should score above 0.5.

    The test text is crafted to trigger the boilerplate signal (many known
    phrases) as well as the short-sentence signal (several fragments under
    6 words), pushing the combined score comfortably above 0.5.
    """
    # Short declarative fragments trigger the short-sentence signal.
    # Dense boilerplate phrases trigger the boilerplate-density signal.
    text = (
        "In conclusion. Certainly! Absolutely. Of course. Great question. "
        "It is important to note that as an AI I cannot delve further. "
        "It's worth noting this. Certainly true. Absolutely correct."
    )
    result = score(text)
    assert result > 0.5, f"Expected score > 0.5 for boilerplate-heavy text, got {result}"


def test_repeated_trigrams_increase_score() -> None:
    """Text with heavily repeated phrases should score above 0.3."""
    # Repeat the same three-word chunk many times to generate duplicate trigrams.
    repeated_phrase = "the quick brown " * 20
    result = score(repeated_phrase.strip())
    assert result > 0.3, f"Expected score > 0.3 for repeated trigrams, got {result}"


def test_score_clamped_to_unit_interval() -> None:
    """score() always returns a value in [0.0, 1.0]."""
    texts = [
        "",
        "Hello.",
        "In conclusion. Certainly. Absolutely. Of course. Great question. Delve. "
        "In conclusion. It is important to note. It's worth noting. As an AI. "
        "I cannot. " * 10,
    ]
    for text in texts:
        result = score(text)
        assert 0.0 <= result <= 1.0, f"Score {result} out of [0, 1] for text: {text!r}"


def test_empty_text_returns_zero() -> None:
    """An empty string should produce a score of exactly 0.0."""
    assert score("") == 0.0
    assert score("   ") == 0.0
