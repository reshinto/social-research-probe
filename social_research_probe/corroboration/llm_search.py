"""LLM-backed agentic-search corroboration backend (runner-agnostic).

The class is :class:`LLMSearchBackend` and this module lives at
``corroboration.llm_search`` because the implementation is **not
Gemini-specific** — it dispatches through whichever LLM runner the user
has configured (Gemini google-search, Claude ``web_search``, Codex
``--search``) via the :class:`~social_research_probe.llm.base.LLMRunner`
abstraction.

**Registry key is ``"llm_search"``** — the runner-agnostic name that
matches the module. Configure via ``[corroboration] backend =
"llm_search"`` or let ``backend = "auto"`` include it during backend
discovery.

Flow:
    1. Resolve the active LLM runner from user config.
    2. If the runner does not support agentic search, return a no-op result
       (``health_check`` gates most callers so this is a defensive path).
    3. Invoke ``runner.agentic_search(claim.text)``; apply the source-quality
       filter from :mod:`._filters` to strip self-source URLs and video-host
       domains; classify the answer into a verdict and wrap in a
       :class:`CorroborationResult`.
"""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.corroboration._filters import filter_results
from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.registry import register
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.llm.base import CapabilityUnavailableError, LLMRunner
from social_research_probe.llm.registry import get_runner
from social_research_probe.llm.types import AgenticSearchResult
from social_research_probe.utils.display.progress import log

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


def _resolve_active_runner() -> LLMRunner | None:
    """Return the user's configured LLM runner, or ``None`` when unavailable.

    Honours ``config.llm_runner``; returns ``None`` when the runner is set to
    ``"none"`` or when the configured runner cannot be instantiated (e.g.
    binary missing). Callers treat ``None`` as "skip this backend".
    """
    cfg = load_active_config()
    if hasattr(cfg, "service_enabled") and not cfg.service_enabled("llm"):
        return None
    if hasattr(cfg, "technology_enabled") and not cfg.technology_enabled("llm_search"):
        return None
    runner_name = cfg.llm_runner
    if runner_name in {"none", "auto"}:
        return None
    if hasattr(cfg, "technology_enabled") and not cfg.technology_enabled(runner_name):
        return None
    try:
        return get_runner(runner_name)
    except KeyError:
        return None


def _filter_citations(result: AgenticSearchResult, source_url: str | None) -> list[str]:
    """Apply the source-quality filter to the runner's citations.

    Delegates to :func:`filter_results` so the same self-source and
    video-domain rules used by Brave/Exa/Tavily apply here too.
    """
    as_dicts = [{"url": c.url, "title": c.title} for c in result.citations if c.url]
    kept, self_excluded, video_excluded = filter_results(as_dicts, source_url)
    if self_excluded or video_excluded:
        log(
            f"[llm_search] filtered {self_excluded} self-source + "
            f"{video_excluded} video-domain citation(s) from "
            f"{len(as_dicts)} (runner={result.runner_name})"
        )
    return [d["url"] for d in kept if d.get("url")]


@register
class LLMSearchBackend(CorroborationBackend):
    """Runner-agnostic agentic-search corroboration backend.

    The class name and module path reflect that this backend is not
    specific to any one LLM; the active runner decides which vendor
    actually performs the search.
    """

    name: ClassVar[str] = "llm_search"

    def health_check(self) -> bool:
        """True iff the configured LLM runner can perform an agentic search.

        Two conditions must hold:
        - ``config.llm_runner`` resolves to a registered runner.
        - That runner flips ``supports_agentic_search = True`` and its own
          ``health_check()`` passes.
        """
        runner = _resolve_active_runner()
        if runner is None:
            return False
        if not runner.supports_agentic_search:
            return False
        try:
            return bool(runner.health_check())
        except Exception:
            return False

    async def corroborate(self, claim) -> CorroborationResult:
        """Run the claim through the active runner's agentic_search and classify."""
        runner = _resolve_active_runner()
        if runner is None or not runner.supports_agentic_search:
            return CorroborationResult(
                verdict="inconclusive",
                confidence=0.0,
                reasoning="no LLM runner with agentic_search capability configured",
                sources=[],
                backend_name=self.name,
            )
        try:
            result = await runner.agentic_search(claim.text)
        except (CapabilityUnavailableError, AdapterError) as exc:
            return CorroborationResult(
                verdict="inconclusive",
                confidence=0.0,
                reasoning=f"agentic_search failed: {exc}",
                sources=[],
                backend_name=self.name,
            )
        sources = _filter_citations(result, getattr(claim, "source_url", None))
        verdict, confidence = _classify_verdict(result.answer)
        return CorroborationResult(
            verdict=verdict,
            confidence=confidence,
            reasoning=result.answer[:500],
            sources=sources,
            backend_name=self.name,
        )
