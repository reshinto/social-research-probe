"""YouTube video sourcing service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult
from social_research_probe.technologies.media_fetch.youtube_api import YoutubeAPIFetch, YoutubeQuery


class YouTubeSourceService(BaseService):
    """Fetch YouTube search results for a list of query configs."""

    service_name: ClassVar[str] = "youtube.sourcing.youtube"
    enabled_config_key: ClassVar[str] = "services.youtube.sourcing.youtube"

    def _get_technologies(self, cfg):
        return [YoutubeAPIFetch()]

    async def execute_batch(self, inputs: list[YoutubeQuery], *, cfg) -> list[ServiceResult]:
        """Run each YoutubeQuery through YoutubeAPIFetch; return one ServiceResult per query."""
        import asyncio

        results = await asyncio.gather(*(self.execute_one(q, cfg=cfg) for q in inputs))
        return list(results)

    async def execute_one(self, data: YoutubeQuery, *, cfg) -> ServiceResult:
        tech = YoutubeAPIFetch()
        tech.caller_service = self.service_name
        try:
            output = await tech.execute(data)
            tr = TechResult(
                tech_name=tech.name, input=data, output=output, success=output is not None
            )
        except Exception as exc:
            tr = TechResult(
                tech_name=tech.name, input=data, output=None, success=False, error=str(exc)
            )
        return ServiceResult(
            service_name=self.service_name, input_key=repr(data), tech_results=[tr]
        )
