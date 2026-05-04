"""YouTubeScoreStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeScoreStage(BaseStage):
    """Score and rank fetched items.

    Examples:
        Input:
            YouTubeScoreStage
        Output:
            YouTubeScoreStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `score` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "score"
        """
        return "score"

    def _top_n_limit(self, state: PipelineState) -> int:
        """Document the top n limit rule at the boundary where callers use it.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Integer count, limit, status code, or timeout used by the caller.

        Examples:
            Input:
                _top_n_limit(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                5
        """
        return int(state.platform_config.get("enrich_top_n", 5))

    def _resolve_purpose_scoring_weights(self, state: PipelineState):
        """Return the resolve purpose scoring weights.

        The YouTube pipeline shares one PipelineState object; this helper documents the part of that
        state this stage reads or writes.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _resolve_purpose_scoring_weights(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                "AI safety"
        """
        merged = state.inputs.get("merged_purpose")
        if merged is None:
            return None
        from social_research_probe.services.scoring import resolve_scoring_weights

        return resolve_scoring_weights(merged)

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube score stage and publish its PipelineState output.

        The YouTube score stage reads the state built so far and publishes the smallest output later
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
        fetch = state.get_stage_output("fetch")
        items = fetch.get("items", [])
        limit = self._top_n_limit(state)

        if not self._is_enabled(state):
            state.set_stage_output("score", {"all_scored": items, "top_n": items[:limit]})
            return state

        weights = self._resolve_purpose_scoring_weights(state)

        from social_research_probe.services.scoring.score import ScoringService

        service = ScoringService()
        result = (
            await service.execute_batch(
                [
                    {
                        "items": items,
                        "engagement_metrics": fetch.get("engagement_metrics", []),
                        "weights": weights,
                        "limit": limit,
                    }
                ]
            )
        )[0]
        score_output = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, dict)),
            {"all_scored": [], "top_n": []},
        )
        state.set_stage_output("score", score_output)
        return state
