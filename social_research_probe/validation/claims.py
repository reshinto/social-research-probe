"""Factual claim extraction from free text.

Why this file exists:
    Downstream corroboration stages need discrete, checkable claims rather than
    raw paragraphs. This module applies lightweight heuristics — sentence
    splitting, word-count filtering, and proper-noun/number detection — to
    identify sentences that are likely to assert a verifiable fact.

Who calls it:
    - The corroboration pipeline passes source text through ``extract_claims``
      to obtain a list of :class:`Claim` objects for fact-checking.

Design notes:
    Uses only the Python standard library. The extraction intentionally errs on
    the side of recall (keeping borderline sentences) so that the downstream
    corroboration step has enough material to work with.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Claim:
    """A single factual claim extracted from source text.

    Lifecycle:
        Created exclusively by :func:`extract_claims`. Consumers treat
        instances as read-only value objects; no mutation is expected.

    Attributes:
        text: The sentence that constitutes the claim.
        source_text: The original passage from which the claim was extracted.
            Useful for attribution and context when displaying results to users.
        index: 0-based position of this claim among all claims extracted from
            the same call to :func:`extract_claims`.
    """

    text: str
    source_text: str
    index: int


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on sentence-ending punctuation.

    Args:
        text: Raw input text, potentially multi-sentence.

    Returns:
        A list of stripped sentence strings. Empty strings are discarded.
    """
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _has_number(sentence: str) -> bool:
    """Return True if the sentence contains at least one digit sequence.

    Why this exists:
        Sentences with numbers (years, statistics, counts) are far more likely
        to be factual claims than purely qualitative statements.

    Args:
        sentence: A single sentence string.

    Returns:
        True if any digit character is present, False otherwise.
    """
    return bool(re.search(r"\d", sentence))


def _has_proper_noun(sentence: str) -> bool:
    """Return True if the sentence contains a proper noun (non-initial capital).

    A word is treated as a proper noun when it starts with an uppercase letter
    and is not the first word of the sentence. This is a simple heuristic that
    catches named entities (people, places, organisations) without requiring an
    NLP library.

    Why this exists:
        Claims about named entities are typically verifiable and therefore
        worth passing to the corroboration pipeline.

    Args:
        sentence: A single sentence string.

    Returns:
        True if at least one interior word begins with an uppercase letter.
    """
    words = sentence.split()
    # Skip the first word — it is always capitalised at the start of a sentence.
    return any(word[0].isupper() for word in words[1:] if word)


def _is_candidate(sentence: str) -> bool:
    """Return True if a sentence meets the minimum quality bar for a claim.

    Criteria (all must hold):
        - At least 5 words (filters out fragments and titles).
        - Contains at least one number OR a proper noun.

    Args:
        sentence: A single sentence string.

    Returns:
        True if the sentence is a candidate claim, False otherwise.
    """
    words = sentence.split()
    if len(words) < 5:
        return False
    return _has_number(sentence) or _has_proper_noun(sentence)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_claims(text: str, source_text: str | None = None) -> list[Claim]:
    """Extract factual claim candidates from the given text.

    Splits ``text`` into sentences, filters to those that are at least 5 words
    long and contain a number or proper noun, then wraps each in a
    :class:`Claim` dataclass.

    Args:
        text: The text to analyse for factual claims. May be empty.
        source_text: The original passage to store on each :class:`Claim` for
            attribution. Defaults to ``text`` when not provided.

    Returns:
        A list of :class:`Claim` objects in sentence order, each with a
        0-based ``index``. Returns an empty list when ``text`` is empty or no
        sentences pass the filters.

    Example::

        claims = extract_claims(
            "The Eiffel Tower was built in 1889. It is tall.",
            source_text="Wikipedia excerpt",
        )
        # → [Claim(text="The Eiffel Tower was built in 1889.", source_text="Wikipedia excerpt", index=0)]
    """
    if not text or not text.strip():
        return []

    resolved_source = source_text if source_text is not None else text
    sentences = _split_sentences(text)

    claims: list[Claim] = []
    for i, sentence in enumerate(s for s in sentences if _is_candidate(s)):
        claims.append(Claim(text=sentence, source_text=resolved_source, index=i))

    return claims
