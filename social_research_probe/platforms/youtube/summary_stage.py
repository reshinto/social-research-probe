"""YouTubeSummaryStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.pipeline.helpers import dict_items, first_tech_output


class YouTubeSummaryStage(BaseStage):
    """Generate LLM summaries for top-N items."""

    @property
    def stage_name(self) -> str:
        return "summary"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.summary import SummaryService

        top_n = list(state.get_stage_output("comments").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("summary", {"top_n": top_n})
            return state
        augmented = await self._items_with_surrogates(top_n)
        summary_results = await SummaryService().execute_batch(dict_items(augmented))
        enriched = self._items_with_summaries(augmented, summary_results)
        state.set_stage_output("summary", {"top_n": enriched})
        return state

    async def _items_with_surrogates(self, top_n: list) -> list:
        from social_research_probe.services.enriching.text_surrogate import TextSurrogateService

        results = await TextSurrogateService().execute_batch(dict_items(top_n))
        return self._merge_surrogates(top_n, results)

    def _merge_surrogates(self, top_n: list, results: list) -> list:
        result_by_index = iter(results)
        augmented = []
        for item in top_n:
            augmented.append(self._item_with_surrogate(item, result_by_index))
        return augmented

    def _item_with_surrogate(self, item: object, result_by_index: object) -> object:
        if not isinstance(item, dict):
            return item
        surrogate = self._surrogate_from_result(next(result_by_index))
        if not isinstance(surrogate, dict):
            return item
        return {
            **item,
            "text_surrogate": surrogate,
            "evidence_tier": surrogate.get("evidence_tier", "metadata_only"),
        }

    def _surrogate_from_result(self, result: object) -> object:
        return first_tech_output(result, dict, require_success=True, require_truthy=True)

    def _items_with_summaries(self, augmented: list, summary_results: list) -> list:
        result_by_index = iter(summary_results)
        enriched: list[dict] = []
        for item in augmented:
            enriched.append(self._item_with_summary(item, result_by_index))
        return enriched

    def _item_with_summary(self, item: object, result_by_index: object) -> object:
        if not isinstance(item, dict):
            return item
        merged = self._summary_from_result(next(result_by_index))
        return merged if isinstance(merged, dict) else dict(item)

    def _summary_from_result(self, result: object) -> object:
        return first_tech_output(result, dict)
