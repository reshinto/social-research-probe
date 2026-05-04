"""Corroboration service: concurrent fact-checking via search providers."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.corroborates import CorroborationHostTech


class CorroborationService(BaseService):
    """Corroborate claims concurrently via configured search providers.

    Input per item: a ScoredItem dict.

    Examples:
        Input:
            CorroborationService
        Output:
            CorroborationService
    """

    service_name: ClassVar[str] = "youtube.corroborating.corroborate"
    enabled_config_key: ClassVar[str] = "services.youtube.corroborating.corroborate"

    def __init__(self, providers: list[str] | None = None):
        """Store constructor options used by later method calls.

        Args:
            providers: Provider names selected for corroboration, search, or fallback execution.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                __init__(
                    providers=["AI safety"],
                )
            Output:
                "AI safety"
        """
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
        """Return the technology adapters this service should run.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _get_technologies()
            Output:
                "AI safety"
        """
        return [CorroborationHostTech(self.providers)]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the corroboration service result.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_service(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
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
