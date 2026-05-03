"""YouTubeSynthesisStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeSynthesisStage(BaseStage):
    """Generate LLM synthesis of all research findings.

    Examples:
        Input:
            YouTubeSynthesisStage
        Output:
            YouTubeSynthesisStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `synthesis` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "synthesis"
        """
        return "synthesis"

    def _build_synthesis_context(self, state: PipelineState) -> dict:
        """Build build synthesis context in the shape consumed by the next project step.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _build_synthesis_context(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                {"enabled": True}
        """
        narratives = state.get_stage_output("narratives")
        corroborate = state.get_stage_output("corroborate")
        score = state.get_stage_output("score")
        fetch = state.get_stage_output("fetch")
        stats = state.get_stage_output("stats")
        charts = state.get_stage_output("charts")
        top_n = list(narratives.get("top_n") or corroborate.get("top_n") or score.get("top_n", []))
        return {
            "top_n": top_n,
            "stats_results": stats.get("stats_summary", {}),
            "chart_results": charts.get("chart_outputs", []),
            "items": fetch.get("items", []),
            "engagement_metrics": fetch.get("engagement_metrics", []),
            "topic": state.inputs.get("topic", ""),
        }

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube synthesis stage and publish its PipelineState output.

        The YouTube synthesis stage reads the state built so far and publishes the smallest output later
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
