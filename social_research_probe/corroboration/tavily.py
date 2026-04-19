"""Tavily search corroboration backend.

What: Implements CorroborationBackend by querying the Tavily search API to find
sources relevant to the claim text. Tavily is optimised for AI agent use-cases
and returns clean, structured results.

Why: Provides a third search signal alongside Exa and Brave, increasing the
robustness of majority-vote aggregation by diversifying the search indices used.

Who calls it: corroboration/host.py via the registry. Requires the environment
variable SRP_TAVILY_API_KEY to be set.
"""
from __future__ import annotations

from typing import ClassVar

from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.registry import register
from social_research_probe.errors import AdapterError


@register
class TavilyBackend(CorroborationBackend):
    """Corroboration backend using the Tavily search API.

    Purpose: Issues a POST search query to Tavily and uses the returned URLs as
    evidence that the claim text appears in publicly reachable sources.

    Lifecycle: Instantiated by get_backend("tavily"); no constructor arguments
    required — API key is read from the environment at call time.

    ABC contract: implements health_check() and corroborate().
    """

    name: ClassVar[str] = "tavily"

    def health_check(self) -> bool:
        """Return True if SRP_TAVILY_API_KEY env var is set.

        Returns:
            True when the key is present and non-empty; False otherwise.
        """
        import os

        return bool(os.environ.get("SRP_TAVILY_API_KEY"))

    def _api_key(self) -> str:
        """Retrieve the Tavily API key from the environment.

        Returns:
            The SRP_TAVILY_API_KEY value as a string.

        Raises:
            AdapterError: if SRP_TAVILY_API_KEY is not set, with a clear message
                so the operator knows exactly which variable to configure.
        """
        import os

        key = os.environ.get("SRP_TAVILY_API_KEY")
        if not key:
            raise AdapterError("SRP_TAVILY_API_KEY not set")
        return key

    def _search(self, query: str) -> list[dict]:  # pragma: no cover — live HTTP
        """Call the Tavily search API and return raw result items.

        Args:
            query: Free-text search query (typically the claim text).

        Returns:
            List of result dicts from Tavily's results array. Each dict has
            at least a "url" key.

        Raises:
            AdapterError: on network failures or missing API key.
        """
        import json
        import urllib.request

        payload = json.dumps({"query": query, "max_results": 5}).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key()}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        # Tavily response structure: {"results": [{"url": ...}, ...]}
        return data.get("results", [])

    def _build_result(self, claim, raw_results: list[dict]) -> CorroborationResult:
        """Convert Tavily API result items into a CorroborationResult.

        Pure function (no I/O) — kept separate from _search() so it can be
        unit-tested with fixture data without making live HTTP calls.

        Args:
            claim: The original Claim dataclass (not used directly here but
                kept for consistency with other backends).
            raw_results: List of result dicts from the Tavily API response.

        Returns:
            A CorroborationResult with verdict='supported' when at least one
            source URL is found, or 'inconclusive' when none are found.
        """
        sources = [r.get("url", "") for r in raw_results if r.get("url")]
        found = len(sources) > 0
        return CorroborationResult(
            verdict="supported" if found else "inconclusive",
            confidence=min(1.0, len(sources) * 0.2),
            reasoning=f"Found {len(sources)} relevant source(s) via Tavily search.",
            sources=sources,
            backend_name=self.name,
        )

    def corroborate(self, claim) -> CorroborationResult:  # pragma: no cover — live HTTP
        """Search Tavily for evidence supporting or refuting the claim.

        Args:
            claim: A Claim dataclass instance. Uses claim.text as the search query.

        Returns:
            CorroborationResult built from the Tavily search API results.

        Raises:
            AdapterError: if the API key is missing or the HTTP call fails.
        """
        raw = self._search(claim.text)
        return self._build_result(claim, raw)
