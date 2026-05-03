"""YouTubeCorroborateStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeCorroborateStage(BaseStage):
    """Corroborate claims in top-N items via configured search providers.

    Examples:
        Input:
            YouTubeCorroborateStage
        Output:
            YouTubeCorroborateStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `corroborate` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "corroborate"
        """
        return "corroborate"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube corroborate stage and publish its PipelineState output.

        The YouTube corroborate stage reads the state built so far and publishes the smallest output
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
        from social_research_probe.services.corroborating.corroborate import CorroborationService

        top_n = list(state.get_stage_output("claims").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state
        service = CorroborationService()
        if not service.providers:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state
        corroboration_inputs = [item for item in top_n if isinstance(item, dict)]
        results = await service.execute_batch(corroboration_inputs)
        corroborated: list[dict] = []
        for result in results:
            item = next(
                (tr.output for tr in result.tech_results if isinstance(tr.output, dict)),
                None,
            )
            if item:
                corroborated.append(item)
        state.set_stage_output("corroborate", {"top_n": corroborated})
        return state
