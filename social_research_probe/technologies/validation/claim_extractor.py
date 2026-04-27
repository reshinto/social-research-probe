"""Claim extraction technology: factual claim candidates from free text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


@dataclass
class Claim:
    """A single factual claim extracted from source text."""

    text: str
    source_text: str
    index: int
    source_url: str | None = None


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _has_number(sentence: str) -> bool:
    return bool(re.search(r"\d", sentence))


def _has_proper_noun(sentence: str) -> bool:
    words = sentence.split()
    return any(word[0].isupper() for word in words[1:] if word)


def _is_candidate(sentence: str) -> bool:
    words = sentence.split()
    if len(words) < 5:
        return False
    return _has_number(sentence) or _has_proper_noun(sentence)


def extract_claims(
    text: str,
    source_text: str | None = None,
    source_url: str | None = None,
) -> list[Claim]:
    """Extract factual claim candidates from free text.

    Unchanged from validation.claims.extract_claims — kept here for callers
    that import from the new technology path.
    """
    if not text or not text.strip():
        return []
    resolved_source = source_text if source_text is not None else text
    sentences = _split_sentences(text)
    claims: list[Claim] = []
    for idx, sentence in enumerate(s for s in sentences if _is_candidate(s)):
        claims.append(
            Claim(
                text=sentence,
                source_text=resolved_source,
                index=idx,
                source_url=source_url,
            )
        )
    return claims


@dataclass
class ClaimExtractorInput:
    """Input for ClaimExtractor.execute()."""

    text: str
    source_text: str | None = None
    source_url: str | None = None


class ClaimExtractor(BaseTechnology[ClaimExtractorInput, list[Claim]]):
    """Technology adapter: extract factual claims from a text string."""

    name: ClassVar[str] = "claim_extractor"
    health_check_key: ClassVar[str] = "claim_extractor"
    enabled_config_key: ClassVar[str] = "claim_extractor"

    async def _execute(self, data: ClaimExtractorInput) -> list[Claim]:
        return extract_claims(data.text, data.source_text, data.source_url)
