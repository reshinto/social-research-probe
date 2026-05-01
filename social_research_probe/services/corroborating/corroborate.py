"""Corroboration service: concurrent fact-checking via search providers."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
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
            from social_research_probe.services.corroborating import (
                select_healthy_providers,
            )
            from social_research_probe.utils.display.fast_mode import (
                FAST_MODE_MAX_PROVIDERS,
                fast_mode_enabled,
            )
            from social_research_probe.utils.display.progress import log

            configured = load_active_config().corroboration_provider
            healthy, candidates = select_healthy_providers(configured)
            if not healthy and candidates:
                checked = ", ".join(candidates)
                log(
                    f"[srp] corroboration: provider '{configured}' configured but no provider usable"
                    f" (checked: {checked}). Hint: run 'srp config check-secrets --corroboration {configured}'."
                )
            self.providers = healthy[:FAST_MODE_MAX_PROVIDERS] if fast_mode_enabled() else healthy
        else:
            self.providers = providers

    def _get_technologies(self):
        return [CorroborationHostTech(self.providers)]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        corroboration = next(
            (tr.output for tr in result.tech_results if tr.success and tr.output),
            None,
        )
        if isinstance(data, dict):
            output = {**data, "corroboration": corroboration} if corroboration else dict(data)
            if result.tech_results:
                result.tech_results[0].output = output
                result.tech_results[0].success = bool(corroboration)
        return result
