"""YouTubeFetchStage implementation."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeFetchStage(BaseStage):
    """Fetch YouTube search results and compute engagement metrics."""

    disable_cache_for_technologies: ClassVar[list[str]] = ["youtube_search", "youtube_hydrate"]

    @property
    def stage_name(self) -> str:
        return "fetch"

    def _resolve_search_topic(self, state: PipelineState) -> str:
        topic = state.inputs.get("topic", "")
        merged = state.inputs.get("merged_purpose")
        if merged is not None:
            from social_research_probe.utils.search.query import enrich_query

            return enrich_query(topic, merged.method)
        return topic

    async def _fetch_items(self, search_topic: str, config: dict) -> tuple[list, list]:
        from social_research_probe.services.sourcing.youtube import YouTubeSourcingService

        result = (await YouTubeSourcingService(config).execute_batch([search_topic]))[0]
        items: list = []
        engagement: list = []
        for tr in result.tech_results:
            if tr.tech_name == "youtube_hydrate" and isinstance(tr.output, list):
                items = tr.output
            elif tr.tech_name == "youtube_engagement" and isinstance(tr.output, list):
                engagement = tr.output
        return items, engagement

    async def execute(self, state: PipelineState) -> PipelineState:
        empty: dict = {"items": [], "engagement_metrics": []}
        if not self._is_enabled(state):
            state.set_stage_output("fetch", empty)
            return state
        search_topic = self._resolve_search_topic(state)
        items, engagement_metrics = await self._fetch_items(search_topic, state.platform_config)
        state.set_stage_output("fetch", {"items": items, "engagement_metrics": engagement_metrics})
        return state
