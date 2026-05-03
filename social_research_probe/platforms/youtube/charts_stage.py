"""YouTubeChartsStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeChartsStage(BaseStage):
    """Render charts for scored items."""

    @property
    def stage_name(self) -> str:
        return "charts"

    def _scored_dataset(self, state: PipelineState) -> list:
        score = state.get_stage_output("score")
        return list(score.get("all_scored") or score.get("top_n", []))

    async def execute(self, state: PipelineState) -> PipelineState:
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
