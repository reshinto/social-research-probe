"""YouTubeSynthesisStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeSynthesisStage(BaseStage):
    """Generate LLM synthesis of all research findings."""

    @property
    def stage_name(self) -> str:
        return "synthesis"

    def _build_synthesis_context(self, state: PipelineState) -> dict:
        corroborate = state.get_stage_output("corroborate")
        score = state.get_stage_output("score")
        fetch = state.get_stage_output("fetch")
        stats = state.get_stage_output("stats")
        charts = state.get_stage_output("charts")
        top_n = list(corroborate.get("top_n") or score.get("top_n", []))
        return {
            "top_n": top_n,
            "stats_results": stats.get("stats_summary", {}),
            "chart_results": charts.get("chart_outputs", []),
            "items": fetch.get("items", []),
            "engagement_metrics": fetch.get("engagement_metrics", []),
            "topic": state.inputs.get("topic", ""),
        }

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.synthesizing.synthesis import SynthesisService

        if not self._is_enabled(state):
            state.set_stage_output("synthesis", {"synthesis": ""})
            return state
        context = self._build_synthesis_context(state)
        result = (await SynthesisService().execute_batch([context]))[0]
        synthesis_text = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, str)),
            "",
        )
        state.set_stage_output("synthesis", {"synthesis": synthesis_text})
        return state
