"""Exa AI search corroboration provider.

What: Implements CorroborationProvider by querying the Exa AI semantic search API
(exa.ai) to find published sources that match the claim text.

Why: Exa specialises in finding semantically similar content, making it effective
at locating whether a claim appears in credible published sources — stronger
evidence than LLM reasoning alone.

Who calls it: corroboration/host.py via the registry. Credentials may come from
SRP_EXA_API_KEY or the active ``secrets.toml``.
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from social_research_probe.technologies.corroborates import (
    CorroborationProvider,
    CorroborationResult,
    filter_results,
    register,
)
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.display.progress import log
from social_research_probe.utils.secrets import HTTP_USER_AGENT, read_runtime_secret


@register
class ExaProvider(CorroborationProvider):
    """Corroboration provider using the Exa AI search API (exa.ai).

    Purpose: Searches for semantically similar content to the claim text and returns the

    URLs of matching sources as evidence.

    Lifecycle: Instantiated by get_provider("exa"); no constructor arguments required — API
    key is read from the environment at call time.

    ABC contract: implements health_check() and corroborate().

    Examples:
        Input:
            ExaProvider
        Output:
            ExaProvider
    """

    name: ClassVar[str] = "exa"
    enabled_config_key: ClassVar[str] = "exa"

    def health_check(self) -> bool:
        """Return True if an Exa API key is available.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                health_check()
            Output:
                True
        """
        return bool(read_runtime_secret("exa_api_key"))

    def _api_key(self) -> str:
        """Retrieve the Exa API key from runtime secret sources.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Raises:
                                    AdapterError: if no Exa API key is configured.



        Examples:
            Input:
                _api_key()
            Output:
                "AI safety"
        """
        key = read_runtime_secret("exa_api_key")
        if not key:
            raise AdapterError(
                "exa_api_key missing — run `srp config set-secret exa_api_key` in a terminal"
            )
        return key

    async def _search(self, query: str) -> list[dict]:
        """Call the Exa search API and return raw result items.

        Corroboration code handles external evidence, so claim shape and provider failure handling stay
        visible here.

        Args:
            query: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                   to a provider.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Raises:
                                    AdapterError: on network failures or non-200 responses.



        Examples:
            Input:
                await _search(
                    query="AI safety benchmarks",
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.exa.ai/search",
                    json={"query": query, "numResults": 5},
                    headers={
                        "x-api-key": self._api_key(),
                        "User-Agent": HTTP_USER_AGENT,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                return resp.json()["results"]
        except (httpx.HTTPError, KeyError) as exc:
            raise AdapterError(f"exa search failed: {exc}") from exc

    def _build_result(self, claim, raw_results: list[dict]) -> CorroborationResult:
        """Convert Exa API result items into a CorroborationResult.

        Pure function (no I/O) — kept separate from _search() so it can be unit-tested
        with fixture data without making live HTTP calls.

        Confidence is capped at 1.0 and scales linearly with the number of sources found

        (0.2 per source), reflecting that more corroborating URLs = higher confidence.

        Args:
            claim: Claim text or claim dictionary being extracted, classified, reviewed, or
                   corroborated.
            raw_results: Provider result records before project-level normalization.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Examples:
            Input:
                _build_result(
                    claim={"text": "The model reduces latency by 30%."},
                    raw_results=["AI safety"],
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        filtered, self_excluded, video_excluded = filter_results(
            raw_results, getattr(claim, "source_url", None)
        )
        if self_excluded or video_excluded:
            log(
                f"[exa] filtered {self_excluded} self-source + "
                f"{video_excluded} video-domain result(s) from {len(raw_results)}"
            )
        sources = [r.get("url", "") for r in filtered if r.get("url")]
        found = len(sources) > 0
        return CorroborationResult(
            verdict="supported" if found else "inconclusive",
            confidence=min(1.0, len(sources) * 0.2),
            reasoning=f"Found {len(sources)} relevant source(s) via Exa search.",
            sources=sources,
            provider_name=self.name,
        )

    async def corroborate(self, claim) -> CorroborationResult:
        """Search Exa for evidence supporting or refuting the claim.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            claim: Claim text or claim dictionary being extracted, classified, reviewed, or
                   corroborated.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Raises:
                                            AdapterError: if the API key is missing or the HTTP call fails.




        Examples:
            Input:
                await corroborate(
                    claim={"text": "The model reduces latency by 30%."},
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        log(f"[srp] exa: searching for claim: {claim.text[:80]!r}")
        raw = await self._search(claim.text)
        return self._build_result(claim, raw)
