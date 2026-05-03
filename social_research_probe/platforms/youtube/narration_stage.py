"""YouTubeNarrationStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeNarrationStage(BaseStage):
    """Read evidence summary aloud via TTS.

    Examples:
        Input:
            YouTubeNarrationStage
        Output:
            YouTubeNarrationStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `narration` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "narration"
        """
        return "narration"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube narration stage and publish its PipelineState output.

        The YouTube narration stage reads the state built so far and publishes the smallest output later
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
        from social_research_probe.services.reporting.audio import AudioReportService

        if not self._is_enabled(state):
            return state

        narration = str(state.outputs.get("report", {}).get("evidence_summary", ""))
        if narration:
            await AudioReportService().execute_batch([{"text": narration}])
        return state
