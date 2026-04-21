"""Gemini CLI google-search corroboration backend.

Fact-checks claims by issuing a google-search-grounded query via the Gemini
CLI. The answer text is classified with a deterministic keyword heuristic to
produce a verdict; the top citations become sources. Fails silent (returns
``inconclusive``) when the Gemini CLI is missing or the adapter errors.
"""

from __future__ import annotations

import shutil
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.registry import register
from social_research_probe.llm.gemini_cli import GeminiSearchResult, gemini_search

_SUPPORT_TOKENS = (
    "support",
    "supported",
    "supports",
    "confirm",
    "confirmed",
    "verified",
    "accurate",
    "true",
    "correct",
    "consistent with",
)
_REFUTE_TOKENS = (
    "refute",
    "refuted",
    "refutes",
    "contradict",
    "contradicts",
    "false",
    "incorrect",
    "misleading",
    "debunked",
    "not supported",
)
_MIXED_TOKENS = ("mixed", "partially", "some truth", "partly true", "nuanced")


def _classify_verdict(answer: str) -> tuple[str, float]:
    """Return (verdict, confidence) from the answer text using keyword families.

    Mixed answers and unmatched answers both map to ``inconclusive`` because
    the base contract only allows supported/refuted/inconclusive.
    """
    text = answer.lower()
    if any(tok in text for tok in _MIXED_TOKENS):
        return ("inconclusive", 0.5)
    support_hits = sum(1 for tok in _SUPPORT_TOKENS if tok in text)
    refute_hits = sum(1 for tok in _REFUTE_TOKENS if tok in text)
    if support_hits > refute_hits and support_hits > 0:
        return ("supported", min(0.5 + 0.1 * support_hits, 0.9))
    if refute_hits > support_hits and refute_hits > 0:
        return ("refuted", min(0.5 + 0.1 * refute_hits, 0.9))
    return ("inconclusive", 0.3)


def _top_source_urls(search: GeminiSearchResult, limit: int = 3) -> list[str]:
    """Return up to ``limit`` citation URLs, skipping empties."""
    urls = [c["url"] for c in search["citations"] if c.get("url")]
    return urls[:limit]


@register
class GeminiSearchBackend(CorroborationBackend):
    """Corroboration backend that uses Gemini CLI's ``--google-search`` flag."""

    name: ClassVar[str] = "gemini_search"

    def health_check(self) -> bool:
        """Return True iff the Gemini CLI binary is present on PATH.

        Uses a sync check (``shutil.which``) because the base contract is sync;
        the async adapter also memoises availability, so call-time cost is
        negligible.
        """
        binary = load_active_config().llm_settings("gemini").get("binary", "gemini")
        return shutil.which(binary) is not None

    async def corroborate(self, claim) -> CorroborationResult:
        """Run the claim through Gemini google-search and return a verdict."""
        search = await gemini_search(claim.text)
        if search is None:
            return CorroborationResult(
                verdict="inconclusive",
                confidence=0.0,
                reasoning="gemini CLI unavailable or returned no usable output",
                sources=[],
                backend_name=self.name,
            )
        verdict, confidence = _classify_verdict(search["answer"])
        return CorroborationResult(
            verdict=verdict,
            confidence=confidence,
            reasoning=search["answer"][:500],
            sources=_top_source_urls(search),
            backend_name=self.name,
        )
