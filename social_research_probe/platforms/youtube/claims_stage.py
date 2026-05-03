"""YouTubeClaimsStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.pipeline.helpers import dict_items, first_tech_output


class YouTubeClaimsStage(BaseStage):
    """Extract structured claims from top-N items."""

    @property
    def stage_name(self) -> str:
        return "claims"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.claims import ClaimExtractionService

        top_n = list(state.get_stage_output("summary").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("claims", {"top_n": top_n})
            return state
        results = await ClaimExtractionService().execute_batch(dict_items(top_n))
        enriched = self._items_with_claims(top_n, results)
        state.set_stage_output("claims", {"top_n": enriched})
        return state

    def _items_with_claims(self, top_n: list, results: list) -> list:
        result_iter = iter(results)
        enriched = []
        for item in top_n:
            enriched.append(self._item_with_claims(item, result_iter))
        return enriched

    def _item_with_claims(self, item: object, result_iter: object) -> object:
        if not isinstance(item, dict):
            return item
        merged = first_tech_output(next(result_iter), dict)
        return merged if isinstance(merged, dict) else {**item, "extracted_claims": []}
