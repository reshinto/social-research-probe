"""Corroboration service: concurrent fact-checking via search providers."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService
from social_research_probe.technologies import BaseTechnology


class CorroborationHostTech(BaseTechnology[object, dict]):
    """Technology wrapper for corroborating a single item's claim."""

    name: ClassVar[str] = "corroboration_host"

    def __init__(self, providers: list[str]):
        self.providers = providers

    async def _execute(self, input_data: object) -> dict:
        from social_research_probe.services.corroborating import corroborate_claim
        from social_research_probe.technologies.validation.claim_extractor import Claim

        title = input_data.get("title", "") if isinstance(input_data, dict) else str(input_data)
        url = input_data.get("url") if isinstance(input_data, dict) else None
        claim = Claim(text=title, source_text=title, index=0, source_url=url)
        return await corroborate_claim(claim, self.providers)


class CorroborationService(BaseService):
    """Corroborate claims concurrently via configured search providers.

    Input per item: a ScoredItem dict.
    """

    service_name: ClassVar[str] = "youtube.corroborating.corroborate"
    enabled_config_key: ClassVar[str] = "services.youtube.corroborating.corroborate"

    def __init__(self, providers: list[str] | None = None):
        if providers is None:
            from social_research_probe.config import load_active_config

            cfg = load_active_config()
            p = getattr(cfg, "corroboration_provider", [])
            self.providers = [p] if isinstance(p, str) else list(p)
        else:
            self.providers = providers

    def _get_technologies(self):
        return [CorroborationHostTech(self.providers)]
