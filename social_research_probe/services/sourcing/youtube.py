"""YouTube sourcing service: search → hydrate → engagement metrics."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.platforms import (
    EngagementMetrics,
    FetchLimits,
    RawItem,
)
from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.technologies.web_search import (
    YouTubeEngagementTech,
    YouTubeHydrateTech,
    YouTubeSearchTech,
)


def _resolve_default_limits() -> FetchLimits:
    platform = load_active_config().platform_defaults("youtube")
    return FetchLimits(
        max_items=int(platform.get("max_items", FetchLimits().max_items)),
        recency_days=platform.get("recency_days", FetchLimits().recency_days),
    )


class YouTubeSourcingService(BaseService[str, dict]):
    """Bundle search → hydrate → engagement metrics for one topic."""

    service_name: ClassVar[str] = "youtube.sourcing"
    enabled_config_key: ClassVar[str] = "services.youtube.sourcing"

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}
        self._search = YouTubeSearchTech()
        self._hydrate = YouTubeHydrateTech()
        self._engagement = YouTubeEngagementTech()

    def _get_technologies(self) -> list[object]:
        return [self._search, self._hydrate, self._engagement]

    async def execute_one(self, data: str) -> ServiceResult:
        """Run the three techs sequentially: search → hydrate → engagement."""
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


async def run_youtube_sourcing(
    topic: str,
    config: dict | None = None,
) -> tuple[list[RawItem], list[EngagementMetrics]]:
    """Run YouTubeSourcingService and return (items, engagement_metrics)."""
    service = YouTubeSourcingService(config)
    result = await service.execute_one(topic)
    items: list[RawItem] = []
    engagement: list[EngagementMetrics] = []
    for tr in result.tech_results:
        if tr.tech_name == YouTubeHydrateTech.name and isinstance(tr.output, list):
            items = tr.output
        elif tr.tech_name == YouTubeEngagementTech.name and isinstance(tr.output, list):
            engagement = tr.output
    return items, engagement
