"""AI-slop detection: heuristic scoring of low-quality AI-generated text.

Why this file exists:
    Large-language-model outputs often exhibit recognisable patterns — repetitive
    boilerplate phrases, duplicated n-grams, and choppy short sentences — that
    correlate with low information density and reduced credibility. This module
    provides a lightweight, dependency-free scorer so the trust-scoring pipeline
    can down-weight sources that look like unedited AI output.

Who calls it:
    - The trust-scoring pipeline (scoring stage) passes candidate text through
      ``score()`` to obtain a slop signal used alongside other quality metrics.

Design notes:
    Three independent signals are combined with equal (1/3) weight. The result
    is always in [0.0, 1.0]: higher means more likely AI slop / low quality.
    All computation uses the Python standard library only.
"""

from __future__ import annotations

import re

_BOILERPLATE_PHRASES: list[str] = [
    "in conclusion",
    "it is important to note",
    "it's worth noting",
    "as an ai",
    "i cannot",
    "delve",
    "certainly",
    "absolutely",
    "of course",
    "great question",
]


def _boilerplate_signal(text: str) -> float:
    """Compute a boilerplate-phrase density score.

    Why this exists:
        AI-generated text frequently reuses a small set of filler phrases.
        Counting these phrases and normalising gives a [0, 1] signal that
        saturates once three or more phrases are detected — a strong slop
        indicator even in short passages.

    Args:
        text: The raw text to analyse (case-insensitive).

    Returns:
        A float in [0.0, 1.0]. 0.0 means no boilerplate phrases found;
        1.0 means three or more were found.
    """
    lower = text.lower()
    count = sum(1 for phrase in _BOILERPLATE_PHRASES if phrase in lower)
    return min(1.0, count / 3)


def _trigrams(words: list[str]) -> list[tuple[str, str, str]]:
    """Return all consecutive 3-word windows from a word list.

    Args:
        words: A flat list of word tokens.

    Returns:
        A list of (word0, word1, word2) tuples, one per window.
        Empty when ``words`` has fewer than 3 elements.
    """
    return [(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)]


def _repetition_signal(text: str) -> float:
    """Compute a trigram-repetition score.

    Why this exists:
        Repetitive LLM outputs often reuse the same multi-word sequences.
        Measuring the fraction of duplicate trigrams catches phrase-level
        repetition that single-word frequency counts miss.

    Args:
        text: The raw text to analyse.

    Returns:
        A float in [0.0, 1.0]. 0.0 means every trigram is unique; 1.0
        means every trigram is a duplicate of an earlier one.
    """
    words = text.lower().split()
    grams = _trigrams(words)
    total = len(grams)
    if total == 0:
        return 0.0

    seen: set[tuple[str, str, str]] = set()
    duplicates = 0
    for gram in grams:
        if gram in seen:
            duplicates += 1
        else:
            seen.add(gram)

    return duplicates / total


def _short_sentence_signal(text: str) -> float:
    """Compute the ratio of short sentences (< 6 words) to total sentences.

    Why this exists:
        AI summaries are sometimes padded with many very short declarative
        sentences. A high proportion of sub-6-word sentences relative to the
        total is a mild slop signal — it suggests fragmented, low-density
        writing rather than coherent prose.

    Args:
        text: The raw text to analyse.

    Returns:
        A float in [0.0, 1.0]. 0.0 if fewer than 2 sentences are present
        (not enough data to judge); otherwise the fraction of sentences with
        fewer than 6 words.
    """
    # Split on sentence-ending punctuation followed by whitespace.
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) < 2:
        return 0.0

    short_count = sum(1 for s in sentences if len(s.split()) < 6)
    return short_count / len(sentences)


def score(text: str) -> float:
    """Return a slop score for the given text.

    Combines three equal-weight signals:
        1. Boilerplate phrase density (saturates at 3 phrases → 1.0).
        2. Trigram repetition ratio (duplicate trigrams / total trigrams).
        3. Short-sentence ratio (sentences < 6 words / total sentences;
           0.0 when fewer than 2 sentences are present).

    Args:
        text: Any string of natural language. May be empty.

    Returns:
        A float in [0.0, 1.0]. Higher values indicate more likely AI slop
        or low-quality content. An empty string returns 0.0.

    Example::

        from social_research_probe.validation.ai_slop import score
        print(score("In conclusion, it is important to note that delve deeply."))
        # → e.g. 0.78
    """
    if not text or not text.strip():
        return 0.0

    combined = (
        _boilerplate_signal(text) + _repetition_signal(text) + _short_sentence_signal(text)
    ) / 3

    # Clamp to [0.0, 1.0] as a defensive measure against floating-point drift.
    return max(0.0, min(1.0, combined))
