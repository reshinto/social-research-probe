"""YouTubeFetchStage implementation."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeFetchStage(BaseStage):
    """Fetch YouTube search results and compute engagement metrics.

    Examples:
        Input:
            YouTubeFetchStage
        Output:
            YouTubeFetchStage()
    """

    disable_cache_for_technologies: ClassVar[list[str]] = ["youtube_search", "youtube_hydrate"]

    @property
    def stage_name(self) -> str:
        """Return the `fetch` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "fetch"
        """
        return "fetch"

    def _resolve_search_topic(self, state: PipelineState) -> str:
        """Document the resolve search topic rule at the boundary where callers use it.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Examples:
            Input:
                _resolve_search_topic(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                "AI safety"
        """
        topic = state.inputs.get("topic", "")
        merged = state.inputs.get("merged_purpose")
        if merged is not None:
            from social_research_probe.utils.search.query import enrich_query

            return enrich_query(topic, merged.method)
        return topic

    async def _fetch_items(self, search_topic: str, config: dict) -> tuple[list, list]:
        """Fetch items without exposing provider details to callers.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            search_topic: Topic string sent to the platform search adapter.
            config: Configuration or context values that control this run.

        Returns:
            Tuple whose positions are part of the public helper contract shown in the example.

        Examples:
            Input:
                await _fetch_items(
                    search_topic="AI safety",
                    config={"enabled": True},
                )
            Output:
                ("AI safety", "Find unmet needs")
        """
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
        """Run the YouTube fetch stage and publish its PipelineState output.

        The YouTube fetch stage reads the state built so far and publishes the smallest output later
        stages need.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            The same PipelineState instance after this stage has published its output.

        Examples:
            Input:
                await execute(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                PipelineState(platform_type="youtube", cmd=None, cache=None)
        """
        empty: dict = {"items": [], "engagement_metrics": []}
        if not self._is_enabled(state):
            state.set_stage_output("fetch", empty)
            return state
        search_topic = self._resolve_search_topic(state)
        items, engagement_metrics = await self._fetch_items(search_topic, state.platform_config)
        state.set_stage_output("fetch", {"items": items, "engagement_metrics": engagement_metrics})
        return state
