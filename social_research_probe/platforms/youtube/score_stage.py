"""YouTubeScoreStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeScoreStage(BaseStage):
    """Score and rank fetched items."""

    @property
    def stage_name(self) -> str:
        return "score"

    def _top_n_limit(self, state: PipelineState) -> int:
        return int(state.platform_config.get("enrich_top_n", 5))

    def _resolve_purpose_scoring_weights(self, state: PipelineState):
        merged = state.inputs.get("merged_purpose")
        if merged is None:
            return None
        from social_research_probe.services.scoring import resolve_scoring_weights

        return resolve_scoring_weights(merged)

    async def execute(self, state: PipelineState) -> PipelineState:
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
