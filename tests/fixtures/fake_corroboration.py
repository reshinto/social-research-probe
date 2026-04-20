"""Deterministic corroboration backends for subprocess integration tests.

Imported only when ``SRP_TEST_USE_FAKE_CORROBORATION=1`` so the end-to-end
CLI tests can exercise host-mode backend discovery without making network
requests to Exa or Tavily.
"""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.corroboration._secret_utils import read_runtime_secret
from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.registry import register


def _sources(prefix: str, claim_text: str) -> list[str]:
    slug = "-".join(claim_text.lower().split()[:4]) or "claim"
    return [f"https://{prefix}.test/{slug}/1", f"https://{prefix}.test/{slug}/2"]


@register
class FakeExaBackend(CorroborationBackend):
    """Test double that behaves like Exa without leaving the machine."""

    name: ClassVar[str] = "exa"

    def health_check(self) -> bool:
        return bool(read_runtime_secret("exa_api_key"))

    async def corroborate(self, claim) -> CorroborationResult:
        return CorroborationResult(
            verdict="supported",
            confidence=0.84,
            reasoning="Fake Exa corroboration for integration tests.",
            sources=_sources("exa", claim.text),
            backend_name=self.name,
        )


@register
class FakeTavilyBackend(CorroborationBackend):
    """Test double that behaves like Tavily without leaving the machine."""

    name: ClassVar[str] = "tavily"

    def health_check(self) -> bool:
        return bool(read_runtime_secret("tavily_api_key"))

    async def corroborate(self, claim) -> CorroborationResult:
        return CorroborationResult(
            verdict="supported",
            confidence=0.79,
            reasoning="Fake Tavily corroboration for integration tests.",
            sources=_sources("tavily", claim.text),
            backend_name=self.name,
        )
