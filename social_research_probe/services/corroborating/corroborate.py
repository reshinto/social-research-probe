"""Corroboration service: concurrent fact-checking via search providers."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult
from social_research_probe.utils.display.progress import log_with_time


class CorroborationService(BaseService):
    """Corroborate claims concurrently via configured search providers.

    Uses asyncio.Semaphore(3) to respect provider rate limits.
    Input per item: a ScoredItem dict.
    """

    service_name: ClassVar[str] = "youtube.corroborating.corroborate"
    enabled_config_key: ClassVar[str] = "services.youtube.corroborating.corroborate"

    def _get_technologies(self):
        return []

    @log_with_time("[srp] {self.service_name}: execute_one")
    async def execute_one(self, data: object) -> ServiceResult:
        """Corroborate one ScoredItem via its title as the claim text."""
        from social_research_probe.config import load_active_config
        from social_research_probe.services.corroborating.host import corroborate_claim
        from social_research_probe.technologies.validation.claim_extractor import Claim

        cfg = load_active_config()
        title = data.get("title", "") if isinstance(data, dict) else str(data)
        url = data.get("url") if isinstance(data, dict) else None
        claim = Claim(text=title, source_text=title, index=0, source_url=url)
        providers = cfg.corroboration_provider if hasattr(cfg, "corroboration_provider") else []
        if isinstance(providers, str):
            providers = [providers]
        try:
            result = await corroborate_claim(claim, providers)
            tr = TechResult(tech_name="corroboration_host", input=data, output=result, success=True)
        except Exception as exc:
            tr = TechResult(
                tech_name="corroboration_host",
                input=data,
                output=None,
                success=False,
                error=str(exc),
            )
        return ServiceResult(service_name=self.service_name, input_key=title, tech_results=[tr])
