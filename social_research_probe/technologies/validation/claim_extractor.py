"""Claim extraction technology: factual claim candidates from free text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


@dataclass
class Claim:
    """A single factual claim extracted from source text.

    Examples:
        Input:
            Claim
        Output:
            Claim
    """

    text: str
    source_text: str
    index: int
    source_url: str | None = None


def _split_sentences(text: str) -> list[str]:
    """Split sentences into smaller units for classification.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _split_sentences(
                text="This tool reduces latency by 30%.",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _has_number(sentence: str) -> bool:
    """Return whether has number is true for the input.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        sentence: Source text, prompt text, or raw value being parsed, normalized, classified, or
                  sent to a provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _has_number(
                sentence="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    return bool(re.search(r"\d", sentence))


def _has_proper_noun(sentence: str) -> bool:
    """Return whether has proper noun is true for the input.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        sentence: Source text, prompt text, or raw value being parsed, normalized, classified, or
                  sent to a provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _has_proper_noun(
                sentence="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    words = sentence.split()
    return any(word[0].isupper() for word in words[1:] if word)


def _is_candidate(sentence: str) -> bool:
    """Return whether is candidate is true for the input.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        sentence: Source text, prompt text, or raw value being parsed, normalized, classified, or
                  sent to a provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_candidate(
                sentence="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
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

    Unchanged from validation.claims.extract_claims — kept here for callers that import from
    the new technology path.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        source_text: Source text, prompt text, or raw value being parsed, normalized, classified, or
                     sent to a provider.
        source_url: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            extract_claims(
                text="This tool reduces latency by 30%.",
                source_text="This tool reduces latency by 30%.",
                source_url="https://youtu.be/abc123",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
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
    """Input for ClaimExtractor.execute().

    Examples:
        Input:
            ClaimExtractorInput
        Output:
            ClaimExtractorInput
    """

    text: str
    source_text: str | None = None
    source_url: str | None = None


class ClaimExtractor(BaseTechnology[ClaimExtractorInput, list[Claim]]):
    """Technology adapter: extract factual claims from a text string.

    Examples:
        Input:
            ClaimExtractor
        Output:
            ClaimExtractor
    """

    name: ClassVar[str] = "claim_extractor"
    health_check_key: ClassVar[str] = "claim_extractor"
    enabled_config_key: ClassVar[str] = "claim_extractor"

    async def _execute(self, data: ClaimExtractorInput) -> list[Claim]:
        """Run this component and return the project-shaped output expected by its service.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        return extract_claims(data.text, data.source_text, data.source_url)
