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
    """Format origin sources for display or files.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Args:
        urls: URLs collected from provider search results.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _format_origin_sources(
                urls=["AI safety"],
            )
        Output:
            "AI safety"
    """
    cleaned = [u for u in urls if u]
    if not cleaned:
        return "(none provided)"
    return "\n".join(f"- {u}" for u in cleaned)


def _build_prompt(claim_text: str, origin_urls: list[str]) -> str:
    """Build the prompt structure consumed by the next step.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Args:
        claim_text: Claim text or claim dictionary being extracted, classified, reviewed, or
                    corroborated.
        origin_urls: Original source URLs used to keep corroboration citations traceable.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _build_prompt(
                claim_text={"text": "The model reduces latency by 30%."},
                origin_urls=["AI safety"],
            )
        Output:
            "AI safety"
    """
    from social_research_probe.utils.llm.prompts import (
        LLM_SEARCH_CORROBORATION_PROMPT,
    )

    return LLM_SEARCH_CORROBORATION_PROMPT.format(
        claim_text=claim_text,
        origin_sources=_format_origin_sources(origin_urls),
    )


def _coerce_verdict(value: object) -> str:
    """Convert an untyped value into a safe verdict value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _coerce_verdict(
                value="42",
            )
        Output:
            "AI safety"
    """
    if isinstance(value, str) and value in _VERDICT_VALUES:
        return value
    return "inconclusive"


def _coerce_confidence(value: object) -> float:
    """Convert an untyped value into a safe confidence value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _coerce_confidence(
                value="42",
            )
        Output:
            0.75
    """
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def _coerce_sources(value: object) -> list[str]:
    """Convert an untyped value into a safe sources value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _coerce_sources(
                value="42",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    if not isinstance(value, list):
        return []
    return [str(s) for s in value if s]


def _parse_response(payload: dict) -> tuple[str, float, str, list[str]]:
    """Parse response into the project format.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        payload: Input payload at this service, technology, or pipeline boundary.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _parse_response(
                payload={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    verdict = _coerce_verdict(payload.get("verdict"))
    confidence = _coerce_confidence(payload.get("confidence"))
    reasoning = str(payload.get("reasoning") or "")
    sources = _coerce_sources(payload.get("sources"))
    return verdict, confidence, reasoning, sources


def _preferred_runner() -> str:
    """Choose the configured LLM runner before falling back to the default runner.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _preferred_runner()
        Output:
            "codex"
    """
    from social_research_probe.config import load_active_config

    return load_active_config().llm_runner


def _run_llm(prompt: str) -> dict:
    """Run the selected LLM runner and normalize its response for callers.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Args:
        prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                to a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _run_llm(
                prompt="Summarize this source.",
            )
        Output:
            {"enabled": True}
    """
    from social_research_probe.utils.llm.registry import run_with_fallback

    return run_with_fallback(prompt, schema=_RESPONSE_SCHEMA, preferred=_preferred_runner())


def _origin_urls_for(claim) -> list[str]:
    """Document the origin urls for rule at the boundary where callers use it.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Args:
        claim: Claim text or claim dictionary being extracted, classified, reviewed, or
               corroborated.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _origin_urls_for(
                claim={"text": "The model reduces latency by 30%."},
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    url = getattr(claim, "source_url", None)
    return [url] if url else []


@register
class LLMSearchProvider(CorroborationProvider):
    """Corroboration provider that delegates to the active LLM runner.

    Lifecycle: Instantiated by ``get_provider("llm_search")``. Holds no state between calls

    — every corroborate() call resolves the preferred runner fresh so config changes take
    effect immediately.

    Examples:
        Input:
            LLMSearchProvider
        Output:
            LLMSearchProvider
    """

    name: ClassVar[str] = "llm_search"
    enabled_config_key: ClassVar[str] = "llm_search"

    def health_check(self) -> bool:
        """Return True when at least one registered LLM runner is healthy.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                health_check()
            Output:
                True
        """
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
        """Document the ask llm rule at the boundary where callers use it.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            claim_text: Claim text or claim dictionary being extracted, classified, reviewed, or
                        corroborated.
            origin_urls: Original source URLs used to keep corroboration citations traceable.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _ask_llm(
                    claim_text={"text": "The model reduces latency by 30%."},
                    origin_urls=["AI safety"],
                )
            Output:
                {"enabled": True}
        """
        prompt = _build_prompt(claim_text, origin_urls)
        return await asyncio.to_thread(_run_llm, prompt)

    def _build_result(self, payload: dict) -> CorroborationResult:
        """Build the result structure consumed by the next step.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            payload: Input payload at this service, technology, or pipeline boundary.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Examples:
            Input:
                _build_result(
                    payload={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        verdict, confidence, reasoning, sources = _parse_response(payload)
        return CorroborationResult(
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning or "LLM returned no reasoning.",
            sources=sources,
            provider_name=self.name,
        )

    async def _try_agentic_search(self, claim_text: str) -> CorroborationResult | None:
        """Try each web search tech in order; return first successful result or None.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            claim_text: Claim text or claim dictionary being extracted, classified, reviewed, or
                        corroborated.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Examples:
            Input:
                await _try_agentic_search(
                    claim_text={"text": "The model reduces latency by 30%."},
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        from social_research_probe.technologies.web_search import (
            ClaudeWebSearch,
            CodexWebSearch,
            GeminiWebSearch,
        )

        for technology in (ClaudeWebSearch(), GeminiWebSearch(), CodexWebSearch()):
            result = await technology.execute(claim_text)
            if result:
                return CorroborationResult(
                    verdict="inconclusive",
                    confidence=0.5,
                    reasoning=result,
                    sources=[],
                    provider_name=self.name,
                )
        return None

    async def corroborate(self, claim) -> CorroborationResult:
        """Document the corroborate rule at the boundary where callers use it.

        Extraction, review, corroboration, and reporting all need the same claim shape.

        Args:
            claim: Claim text or claim dictionary being extracted, classified, reviewed, or
                   corroborated.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Examples:
            Input:
                await corroborate(
                    claim={"text": "The model reduces latency by 30%."},
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        log(f"[srp] llm_search: assessing claim: {claim.text[:80]!r}")
        agentic = await self._try_agentic_search(claim.text)
        if agentic is not None:
            return agentic
        payload = await self._ask_llm(claim.text, _origin_urls_for(claim))
        return self._build_result(payload)
