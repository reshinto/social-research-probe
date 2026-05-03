"""Tavily search corroboration provider.

What: Implements CorroborationProvider by querying the Tavily search API to find
sources relevant to the claim text. Tavily is optimised for AI agent use-cases
and returns clean, structured results.

Why: Provides a third search signal alongside Exa and Brave, increasing the
robustness of majority-vote aggregation by diversifying the search indices used.

Who calls it: corroboration/host.py via the registry. Credentials may come from
SRP_TAVILY_API_KEY or the active ``secrets.toml``.
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
class TavilyProvider(CorroborationProvider):
    """Corroboration provider using the Tavily search API.

    Purpose: Issues a POST search query to Tavily and uses the returned URLs as evidence
    that the claim text appears in publicly reachable sources.

    Lifecycle: Instantiated by get_provider("tavily"); no constructor arguments required —

    API key is read from the environment at call time.

    ABC contract: implements health_check() and corroborate().

    Examples:
        Input:
            TavilyProvider
        Output:
            TavilyProvider
    """

    name: ClassVar[str] = "tavily"
    enabled_config_key: ClassVar[str] = "tavily"

    def health_check(self) -> bool:
        """Return True if a Tavily API key is available.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                health_check()
            Output:
                True
        """
        return bool(read_runtime_secret("tavily_api_key"))

    def _api_key(self) -> str:
        """Retrieve the Tavily API key from runtime secret sources.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Raises:
                                    AdapterError: if no Tavily API key is configured.



        Examples:
            Input:
                _api_key()
            Output:
                "AI safety"
        """
        key = read_runtime_secret("tavily_api_key")
        if not key:
            raise AdapterError(
                "tavily_api_key missing — run `srp config set-secret tavily_api_key` in a terminal"
            )
        return key

    async def _search(self, query: str) -> list[dict]:
        """Call the Tavily search API and return raw result items.

        Corroboration code handles external evidence, so claim shape and provider failure handling stay
        visible here.

        Args:
            query: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                   to a provider.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Raises:
                                    AdapterError: on network failures or missing API key.



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
                    "https://api.tavily.com/search",
                    json={"query": query, "max_results": 5},
                    headers={
                        "Authorization": f"Bearer {self._api_key()}",
                        "User-Agent": HTTP_USER_AGENT,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                return resp.json().get("results", [])
        except httpx.HTTPError as exc:
            raise AdapterError(f"tavily search failed: {exc}") from exc

    def _build_result(self, claim, raw_results: list[dict]) -> CorroborationResult:
        """Convert Tavily API result items into a CorroborationResult.

        Pure function (no I/O) — kept separate from _search() so it can be unit-tested
        with fixture data without making live HTTP calls.

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
                f"[tavily] filtered {self_excluded} self-source + "
                f"{video_excluded} video-domain result(s) from {len(raw_results)}"
            )
        sources = [r.get("url", "") for r in filtered if r.get("url")]
        found = len(sources) > 0
        return CorroborationResult(
            verdict="supported" if found else "inconclusive",
            confidence=min(1.0, len(sources) * 0.2),
            reasoning=f"Found {len(sources)} relevant source(s) via Tavily search.",
            sources=sources,
            provider_name=self.name,
        )

    async def corroborate(self, claim) -> CorroborationResult:
        """Search Tavily for evidence supporting or refuting the claim.

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
        log(f"[srp] tavily: searching for claim: {claim.text[:80]!r}")
        raw = await self._search(claim.text)
        return self._build_result(claim, raw)
