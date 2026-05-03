"""YouTubeStatsStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeStatsStage(BaseStage):
    """Compute statistics on scored items.

    Examples:
        Input:
            YouTubeStatsStage
        Output:
            YouTubeStatsStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `stats` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "stats"
        """
        return "stats"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube stats stage and publish its PipelineState output.

        The YouTube stats stage reads the state built so far and publishes the smallest output later
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
        from social_research_probe.services.analyzing.statistics import StatisticsService

        if not self._is_enabled(state):
            state.set_stage_output("stats", {"stats_summary": {}})
            return state

        top_n = list(state.get_stage_output("score").get("top_n", []))
        result = (await StatisticsService().execute_batch([{"scored_items": top_n}]))[0]
        stats_output = next((tr.output for tr in result.tech_results if tr.success), None)
        state.set_stage_output(
            "stats",
            {"stats_summary": stats_output if isinstance(stats_output, dict) else {}},
        )
        return state
