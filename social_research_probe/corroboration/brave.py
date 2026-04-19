"""Brave Search corroboration backend.

What: Implements CorroborationBackend by querying the Brave Search web API to
find pages that match the claim text.

Why: Brave Search returns traditional web index results (not AI-generated),
giving a complementary signal to semantic-search backends like Exa.

Who calls it: corroboration/host.py via the registry. Requires the environment
variable SRP_BRAVE_API_KEY to be set.
"""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.registry import register
from social_research_probe.errors import AdapterError


@register
class BraveBackend(CorroborationBackend):
    """Corroboration backend using the Brave Search web API.

    Purpose: Issues a standard web search query and uses the resulting URLs as
    evidence that the claim text appears in publicly indexed sources.

    Lifecycle: Instantiated by get_backend("brave"); no constructor arguments
    required — API key is read from the environment at call time.

    ABC contract: implements health_check() and corroborate().
    """

    name: ClassVar[str] = "brave"

    def health_check(self) -> bool:
        """Return True if SRP_BRAVE_API_KEY env var is set.

        Returns:
            True when the key is present and non-empty; False otherwise.
        """
        import os

        return bool(os.environ.get("SRP_BRAVE_API_KEY"))

    def _api_key(self) -> str:
        """Retrieve the Brave API key from the environment.

        Returns:
            The SRP_BRAVE_API_KEY value as a string.

        Raises:
            AdapterError: if SRP_BRAVE_API_KEY is not set, with a clear message
                so the operator knows exactly which variable to configure.
        """
        import os

        key = os.environ.get("SRP_BRAVE_API_KEY")
        if not key:
            raise AdapterError("SRP_BRAVE_API_KEY not set")
        return key

    def _search(self, query: str) -> list[dict]:
        """Call the Brave Search API and return raw web result items.

        Args:
            query: Free-text search query (typically the claim text).

        Returns:
            List of result dicts from the Brave API's web.results array.
            Each dict has at least a "url" key.

        Raises:
            AdapterError: on network failures or missing API key.
        """
        import json
        import urllib.error
        import urllib.parse
        import urllib.request

        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://api.search.brave.com/res/v1/web/search?q={encoded_query}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self._api_key(),
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as exc:
            raise AdapterError(f"brave search failed: {exc}") from exc
        return data.get("web", {}).get("results", [])

    def _build_result(self, claim, raw_results: list[dict]) -> CorroborationResult:
        """Convert Brave API result items into a CorroborationResult.

        Pure function (no I/O) — kept separate from _search() so it can be
        unit-tested with fixture data without making live HTTP calls.

        Args:
            claim: The original Claim dataclass (not used directly here but
                kept for consistency with other backends).
            raw_results: List of result dicts from the Brave API's web.results.

        Returns:
            A CorroborationResult with verdict='supported' when at least one
            source URL is found, or 'inconclusive' when none are found.
        """
        sources = [r.get("url", "") for r in raw_results if r.get("url")]
        found = len(sources) > 0
        return CorroborationResult(
            verdict="supported" if found else "inconclusive",
            confidence=min(1.0, len(sources) * 0.2),
            reasoning=f"Found {len(sources)} relevant source(s) via Brave Search.",
            sources=sources,
            backend_name=self.name,
        )

    def corroborate(self, claim) -> CorroborationResult:
        """Search Brave for evidence supporting or refuting the claim.

        Args:
            claim: A Claim dataclass instance. Uses claim.text as the search query.

        Returns:
            CorroborationResult built from the Brave Search API results.

        Raises:
            AdapterError: if the API key is missing or the HTTP call fails.
        """
        print(f"[srp] brave: searching for claim: {claim.text[:80]!r}")
        raw = self._search(claim.text)
        return self._build_result(claim, raw)
