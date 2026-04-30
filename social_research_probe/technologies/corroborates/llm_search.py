"""LLM-search corroboration provider.

What: Implements CorroborationProvider by asking the configured LLM runner
to assess whether a claim is supported, refuted, or inconclusive based on its
training-data knowledge. Returns structured JSON via a strict schema.

Why: When dedicated search APIs (Exa, Brave, Tavily) are unavailable or rate
limited, the LLM still offers a useful sanity-check signal. Cheap fallback
that requires no extra API key beyond the active LLM runner.

Who calls it: corroboration/host.py via the registry. Runner selection is
handled by services/llm/registry.run_with_fallback so any healthy runner can
serve the call.
"""

from __future__ import annotations

import asyncio
from typing import ClassVar

from social_research_probe.technologies.corroborates import (
    CorroborationProvider,
    CorroborationResult,
    register,
)
from social_research_probe.utils.display.progress import log

_VERDICT_VALUES: tuple[str, ...] = ("supported", "refuted", "inconclusive")

_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(_VERDICT_VALUES)},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reasoning": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "confidence", "reasoning"],
    "additionalProperties": False,
}


def _format_origin_sources(urls: list[str]) -> str:
    cleaned = [u for u in urls if u]
    if not cleaned:
        return "(none provided)"
    return "\n".join(f"- {u}" for u in cleaned)


def _build_prompt(claim_text: str, origin_urls: list[str]) -> str:
    from social_research_probe.utils.llm.prompts import (
        LLM_SEARCH_CORROBORATION_PROMPT,
    )

    return LLM_SEARCH_CORROBORATION_PROMPT.format(
        claim_text=claim_text,
        origin_sources=_format_origin_sources(origin_urls),
    )


def _coerce_verdict(value: object) -> str:
    if isinstance(value, str) and value in _VERDICT_VALUES:
        return value
    return "inconclusive"


def _coerce_confidence(value: object) -> float:
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def _coerce_sources(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(s) for s in value if s]


def _parse_response(payload: dict) -> tuple[str, float, str, list[str]]:
    verdict = _coerce_verdict(payload.get("verdict"))
    confidence = _coerce_confidence(payload.get("confidence"))
    reasoning = str(payload.get("reasoning") or "")
    sources = _coerce_sources(payload.get("sources"))
    return verdict, confidence, reasoning, sources


def _preferred_runner() -> str:
    from social_research_probe.config import load_active_config

    return load_active_config().llm_runner


def _run_llm(prompt: str) -> dict:
    from social_research_probe.utils.llm.registry import run_with_fallback

    return run_with_fallback(prompt, schema=_RESPONSE_SCHEMA, preferred=_preferred_runner())


def _origin_urls_for(claim) -> list[str]:
    url = getattr(claim, "source_url", None)
    return [url] if url else []


@register
class LLMSearchProvider(CorroborationProvider):
    """Corroboration provider that delegates to the active LLM runner.

    Lifecycle: Instantiated by ``get_provider("llm_search")``. Holds no state
    between calls — every corroborate() call resolves the preferred runner
    fresh so config changes take effect immediately.
    """

    name: ClassVar[str] = "llm_search"
    enabled_config_key: ClassVar[str] = "llm_search"

    def health_check(self) -> bool:
        """Return True when at least one registered LLM runner is healthy."""
        from social_research_probe.utils.llm.registry import (
            get_runner,
            list_runners,
        )

        for name in list_runners():
            try:
                if get_runner(name).health_check():
                    return True
            except Exception:
                continue
        return False

    async def _ask_llm(self, claim_text: str, origin_urls: list[str]) -> dict:
        prompt = _build_prompt(claim_text, origin_urls)
        return await asyncio.to_thread(_run_llm, prompt)

    def _build_result(self, payload: dict) -> CorroborationResult:
        verdict, confidence, reasoning, sources = _parse_response(payload)
        return CorroborationResult(
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning or "LLM returned no reasoning.",
            sources=sources,
            provider_name=self.name,
        )

    async def corroborate(self, claim) -> CorroborationResult:
        """Ask the active LLM runner to assess ``claim`` and return a verdict."""
        log(f"[srp] llm_search: assessing claim: {claim.text[:80]!r}")
        payload = await self._ask_llm(claim.text, _origin_urls_for(claim))
        return self._build_result(payload)
