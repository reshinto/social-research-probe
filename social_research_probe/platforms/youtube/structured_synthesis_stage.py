"""YouTubeStructuredSynthesisStage implementation."""

from __future__ import annotations

import asyncio

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeStructuredSynthesisStage(BaseStage):
    """Run structured LLM synthesis on the assembled report and attach results.

    Examples:
        Input:
            YouTubeStructuredSynthesisStage
        Output:
            YouTubeStructuredSynthesisStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `structured_synthesis` stage key used by config and PipelineState.

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
        return "structured_synthesis"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube structured synthesis stage and publish its PipelineState output.

        The YouTube structured synthesis stage reads the state built so far and publishes the smallest
        output later stages need.

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
        if not self._is_enabled(state):
            return state

        from social_research_probe.services.synthesizing.synthesis.runner import attach_synthesis

        report = state.outputs.get("report", {})
        await asyncio.to_thread(attach_synthesis, report)
        state.outputs["report"] = report
        return state
