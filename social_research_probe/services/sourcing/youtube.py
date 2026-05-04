"""YouTube sourcing service: search → hydrate → engagement metrics."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.technologies.media_fetch import (
    YouTubeEngagementTech,
    YouTubeHydrateTech,
    YouTubeSearchTech,
)
from social_research_probe.utils.core.types import FetchLimits


def _resolve_default_limits() -> FetchLimits:
    """Resolve the YouTube fetch limits from active configuration.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _resolve_default_limits()
        Output:
            "AI safety"
    """
    platform = load_active_config().platform_defaults("youtube")
    return FetchLimits(
        max_items=int(platform.get("max_items", FetchLimits().max_items)),
        recency_days=platform.get("recency_days", FetchLimits().recency_days),
    )


class YouTubeSourcingService(BaseService[str, dict]):
    """Bundle search → hydrate → engagement metrics for one topic.

    Examples:
        Input:
            YouTubeSourcingService
        Output:
            YouTubeSourcingService
    """

    service_name: ClassVar[str] = "youtube.sourcing"
    enabled_config_key: ClassVar[str] = "services.youtube.sourcing.youtube"
    run_technologies_concurrently: ClassVar[bool] = False

    def __init__(self, config: dict | None = None) -> None:
        """Store constructor options used by later method calls.

        Args:
            config: Configuration or context values that control this run.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                __init__(
                    config={"enabled": True},
                )
            Output:
                None
        """
        self.config = config or {}
        self._search = YouTubeSearchTech()
        self._hydrate = YouTubeHydrateTech()
        self._engagement = YouTubeEngagementTech()

    def _get_technologies(self) -> list[object]:
        """Return the technology adapters this service is allowed to run.

        Services turn platform items into adapter requests and normalize results so stages handle
        success, skip, and failure the same way.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _get_technologies()
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        return [self._search, self._hydrate, self._engagement]

    async def execute_service(self, data: str, result: ServiceResult) -> ServiceResult:
        """Run the three techs sequentially: search → hydrate → engagement.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

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
        topic = data
        limits = _resolve_default_limits()
        include_shorts = bool(self.config.get("include_shorts", True))

        for tech in self._get_technologies():
            tech.caller_service = self.service_name

        tech_results: list[TechResult] = []

        items = await self._run_tech(self._search, (topic, limits), tech_results)
        if items is None:
            items = []

        hydrated = await self._run_tech(self._hydrate, (items, include_shorts), tech_results)
        if hydrated is None:
            hydrated = items

        engagement = await self._run_tech(self._engagement, hydrated, tech_results)
        if engagement is None:
            engagement = []

        return ServiceResult(
            service_name=self.service_name,
            input_key=topic,
            tech_results=tech_results,
        )

    async def _run_tech(
        self,
        tech: object,
        data: object,
        sink: list[TechResult],
    ) -> object:
        """Run one sourcing adapter and append its result to the shared result list.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            tech: Technology adapter exposing a stable name and execute method.
            data: Input payload at this service, technology, or pipeline boundary.
            sink: Intermediate collection used to preserve ordering while stage results are merged.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await _run_tech(
                    tech=summary_adapter,
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    sink=[],
                )
            Output:
                "AI safety"
        """
        try:
            output = await tech.execute(data)
            sink.append(
                TechResult(
                    tech_name=tech.name,
                    input=data,
                    output=output,
                    success=output is not None,
                )
            )
            return output
        except Exception as exc:
            sink.append(
                TechResult(
                    tech_name=tech.name,
                    input=data,
                    output=None,
                    success=False,
                    error=str(exc),
                )
            )
            return None
