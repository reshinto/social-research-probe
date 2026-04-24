"""Corroboration service: concurrent fact-checking via search backends."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class CorroborationService(BaseService):
    """Corroborate claims concurrently via configured search backends.

    Uses asyncio.Semaphore(3) to respect backend rate limits.
    Input per item: a ScoredItem dict.
    """

    service_name: ClassVar[str] = "youtube.corroborating.corroborate"
    enabled_config_key: ClassVar[str] = "services.youtube.corroborating.corroborate"

    def _get_technologies(self, cfg):
        return []

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Corroborate one ScoredItem via its title as the claim text."""
        from social_research_probe.services.corroborating.host import corroborate_claim
        from social_research_probe.technologies.validation.claim_extractor import Claim

        title = data.get("title", "") if isinstance(data, dict) else str(data)
        url = data.get("url") if isinstance(data, dict) else None
        claim = Claim(text=title, source_text=title, index=0, source_url=url)
        backends = cfg.corroboration_backend if hasattr(cfg, "corroboration_backend") else []
        if isinstance(backends, str):
            backends = [backends]
        try:
            result = await corroborate_claim(claim, backends)
            tr = TechResult(tech_name="corroboration_host", input=data, output=result, success=True)
        except Exception as exc:
            tr = TechResult(tech_name="corroboration_host", input=data, output=None, success=False, error=str(exc))
        return ServiceResult(service_name=self.service_name, input_key=title, tech_results=[tr])
