"""YouTubeTranscriptStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeTranscriptStage(BaseStage):
    """Fetch transcripts for top-N items.

    Examples:
        Input:
            YouTubeTranscriptStage
        Output:
            YouTubeTranscriptStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `transcript` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "transcript"
        """
        return "transcript"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube transcript stage and publish its PipelineState output.

        The YouTube transcript stage reads the state built so far and publishes the smallest output
        later stages need.

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
        from social_research_probe.services.enriching.transcript import TranscriptService

        top_n = list(state.get_stage_output("score").get("top_n", []))
        if not self._is_enabled(state):
            # Preserve the ranked item list while marking transcript evidence as intentionally absent.
            # Downstream stages can then distinguish a configured skip from a provider failure.
            disabled = [
                {**it, "transcript_status": "disabled"} if isinstance(it, dict) else it
                for it in top_n
            ]
            state.set_stage_output("transcript", {"top_n": disabled})
            return state
        if not top_n:
            state.set_stage_output("transcript", {"top_n": top_n})
            return state
        service = TranscriptService()
        transcript_inputs = [item for item in top_n if isinstance(item, dict)]
        results = await service.execute_batch(transcript_inputs)
        enriched: list[dict] = []
        for result in results:
            item = next(
                (tr.output for tr in result.tech_results if isinstance(tr.output, dict)),
                None,
            )
            if item:
                enriched.append(item)
        state.set_stage_output("transcript", {"top_n": enriched})
        return state
