"""Corroboration service: concurrent fact-checking via search providers."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService
from social_research_probe.technologies.corroborates import CorroborationHostTech


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
