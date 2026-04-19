"""Exa AI search corroboration backend.

What: Implements CorroborationBackend by querying the Exa AI semantic search API
(exa.ai) to find published sources that match the claim text.

Why: Exa specialises in finding semantically similar content, making it effective
at locating whether a claim appears in credible published sources — stronger
evidence than LLM reasoning alone.

Who calls it: corroboration/host.py via the registry. Credentials may come from
SRP_EXA_API_KEY or the active ``secrets.toml``.
"""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.corroboration._secret_utils import read_runtime_secret
from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.registry import register
from social_research_probe.errors import AdapterError
from social_research_probe.utils.progress import log


@register
class ExaBackend(CorroborationBackend):
    """Corroboration backend using the Exa AI search API (exa.ai).

    Purpose: Searches for semantically similar content to the claim text and
    returns the URLs of matching sources as evidence.

    Lifecycle: Instantiated by get_backend("exa"); no constructor arguments
    required — API key is read from the environment at call time.

    ABC contract: implements health_check() and corroborate().
    """

    name: ClassVar[str] = "exa"

    def health_check(self) -> bool:
        """Return True if an Exa API key is available.

        Returns:
            True when the key is present and non-empty; False otherwise.
        """
        return bool(read_runtime_secret("exa_api_key"))

    def _api_key(self) -> str:
        """Retrieve the Exa API key from runtime secret sources.

        Returns:
            The Exa API key as a string.

        Raises:
            AdapterError: if no Exa API key is configured.
        """
        key = read_runtime_secret("exa_api_key")
        if not key:
            raise AdapterError(
                "exa_api_key missing — run `srp config set-secret exa_api_key` in a terminal"
            )
        return key

    def _search(self, query: str) -> list[dict]:
        """Call the Exa search API and return raw result items.

        Args:
            query: Free-text search query (typically the claim text).

        Returns:
            List of result dicts as returned by the Exa API (each has at least
            a "url" key).

        Raises:
            AdapterError: on network failures or non-200 responses.
        """
        import json
        import urllib.error
        import urllib.request

        payload = json.dumps({"query": query, "numResults": 5}).encode()
        req = urllib.request.Request(
            "https://api.exa.ai/search",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key(),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())["results"]
        except (urllib.error.URLError, KeyError) as exc:
            raise AdapterError(f"exa search failed: {exc}") from exc

    def _build_result(self, claim, raw_results: list[dict]) -> CorroborationResult:
        """Convert Exa API result items into a CorroborationResult.

        Pure function (no I/O) — kept separate from _search() so it can be
        unit-tested with fixture data without making live HTTP calls.

        Confidence is capped at 1.0 and scales linearly with the number of
        sources found (0.2 per source), reflecting that more corroborating
        URLs = higher confidence.

        Args:
            claim: The original Claim dataclass (not used directly here but
                kept for consistency with other backends).
            raw_results: List of result dicts from the Exa API response.

        Returns:
            A CorroborationResult with verdict='supported' when at least one
            source URL is found, or 'inconclusive' when none are found.
        """
        sources = [r.get("url", "") for r in raw_results if r.get("url")]
        found = len(sources) > 0
        return CorroborationResult(
            verdict="supported" if found else "inconclusive",
            confidence=min(1.0, len(sources) * 0.2),
            reasoning=f"Found {len(sources)} relevant source(s) via Exa search.",
            sources=sources,
            backend_name=self.name,
        )

    def corroborate(self, claim) -> CorroborationResult:
        """Search Exa for evidence supporting or refuting the claim.

        Args:
            claim: A Claim dataclass instance. Uses claim.text as the search query.

        Returns:
            CorroborationResult built from the Exa API search results.

        Raises:
            AdapterError: if the API key is missing or the HTTP call fails.
        """
        log(f"[srp] exa: searching for claim: {claim.text[:80]!r}")
        raw = self._search(claim.text)
        return self._build_result(claim, raw)
