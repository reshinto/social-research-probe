"""YouTubeChartsStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeChartsStage(BaseStage):
    """Render charts for scored items.

    Examples:
        Input:
            YouTubeChartsStage
        Output:
            YouTubeChartsStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `charts` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "charts"
        """
        return "charts"

    def _scored_dataset(self, state: PipelineState) -> list:
        """Compute the scored dataset used by ranking or analysis.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _scored_dataset(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        score = state.get_stage_output("score")
        return list(score.get("all_scored") or score.get("top_n", []))

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube charts stage and publish its PipelineState output.

        The YouTube charts stage reads the state built so far and publishes the smallest output later
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
        from social_research_probe.services.analyzing.charts import ChartsService

        if not self._is_enabled(state):
            state.set_stage_output(
                "charts", {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []}
            )
            return state
        items = self._scored_dataset(state)
        result = (await ChartsService().execute_batch([{"scored_items": items}]))[0]
        charts = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, dict)),
            {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []},
        )
        state.set_stage_output("charts", charts)
        return state
