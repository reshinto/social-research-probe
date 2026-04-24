"""Brave Search corroboration backend.

What: Implements CorroborationBackend by querying the Brave Search web API to
find pages that match the claim text.

Why: Brave Search returns traditional web index results (not AI-generated),
giving a complementary signal to semantic-search backends like Exa.

Who calls it: corroboration/host.py via the registry. Credentials may come from
SRP_BRAVE_API_KEY or the active ``secrets.toml``.
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from social_research_probe.technologies.corroborates._filters import filter_results
from social_research_probe.utils.secrets import HTTP_USER_AGENT, read_runtime_secret
from social_research_probe.technologies.corroborates.base import CorroborationBackend, CorroborationResult
from social_research_probe.services.corroborating.registry import register
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.display.progress import log


@register
class BraveBackend(CorroborationBackend, BaseTechnology):
    """Corroboration backend using the Brave Search web API.

    Purpose: Issues a standard web search query and uses the resulting URLs as
    evidence that the claim text appears in publicly indexed sources.

    Lifecycle: Instantiated by get_backend("brave"); no constructor arguments
    required — API key is read from the environment at call time.

    ABC contract: implements health_check() and corroborate().
    """

    name: ClassVar[str] = "brave"
    health_check_key: ClassVar[str] = "brave"
    enabled_config_key: ClassVar[str] = "brave"

    def health_check(self) -> bool:
        """Return True if a Brave API key is available.

        Returns:
            True when the key is present and non-empty; False otherwise.
        """
        return bool(read_runtime_secret("brave_api_key"))

    def _api_key(self) -> str:
        """Retrieve the Brave API key from runtime secret sources.

        Returns:
            The Brave API key as a string.

        Raises:
            AdapterError: if no Brave API key is configured.
        """
        key = read_runtime_secret("brave_api_key")
        if not key:
            raise AdapterError(
                "brave_api_key missing — run `srp config set-secret brave_api_key` in a terminal"
            )
        return key

    async def _search(self, query: str) -> list[dict]:
        """Call the Brave Search API and return raw web result items.

        Args:
            query: Free-text search query (typically the claim text).

        Returns:
            List of result dicts from the Brave API's web.results array.
            Each dict has at least a "url" key.

        Raises:
            AdapterError: on network failures or missing API key.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query},
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": self._api_key(),
                        "User-Agent": HTTP_USER_AGENT,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
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
        filtered, self_excluded, video_excluded = filter_results(
            raw_results, getattr(claim, "source_url", None)
        )
        if self_excluded or video_excluded:
            log(
                f"[brave] filtered {self_excluded} self-source + "
                f"{video_excluded} video-domain result(s) from {len(raw_results)}"
            )
        sources = [r.get("url", "") for r in filtered if r.get("url")]
        found = len(sources) > 0
        return CorroborationResult(
            verdict="supported" if found else "inconclusive",
            confidence=min(1.0, len(sources) * 0.2),
            reasoning=f"Found {len(sources)} relevant source(s) via Brave Search.",
            sources=sources,
            backend_name=self.name,
        )

    async def corroborate(self, claim) -> CorroborationResult:
        """Search Brave for evidence supporting or refuting the claim.

        Args:
            claim: A Claim dataclass instance. Uses claim.text as the search query.

        Returns:
            CorroborationResult built from the Brave Search API results.

        Raises:
            AdapterError: if the API key is missing or the HTTP call fails.
        """
        log(f"[srp] brave: searching for claim: {claim.text[:80]!r}")
        raw = await self._search(claim.text)
        return self._build_result(claim, raw)

    async def _execute(self, data: object) -> object:
        """BaseTechnology async adapter — delegates to corroborate()."""
        return await self.corroborate(data)
