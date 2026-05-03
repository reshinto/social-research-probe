"""YouTubeSummaryStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.pipeline.helpers import dict_items, first_tech_output


class YouTubeSummaryStage(BaseStage):
    """Generate LLM summaries for top-N items.

    Examples:
        Input:
            YouTubeSummaryStage
        Output:
            YouTubeSummaryStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `summary` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "summary"
        """
        return "summary"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube summary stage and publish its PipelineState output.

        The YouTube summary stage reads the state built so far and publishes the smallest output later
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
        """Run enrichment for each item before attaching surrogates data.

        The report pipeline needs a predictable text payload even when transcripts or summaries are
        missing.

        Args:
            top_n: Ordered source items being carried through the current pipeline step.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _items_with_surrogates(
                    top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        from social_research_probe.services.enriching.text_surrogate import TextSurrogateService

        results = await TextSurrogateService().execute_batch(dict_items(top_n))
        return self._merge_surrogates(top_n, results)

    def _merge_surrogates(self, top_n: list, results: list) -> list:
        """Merge surrogates using the module's precedence rules.

        The report pipeline needs a predictable text payload even when transcripts or summaries are
        missing.

        Args:
            top_n: Ordered source items being carried through the current pipeline step.
            results: Service or technology result being inspected for payload and diagnostics.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _merge_surrogates(
                    top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    results=[ServiceResult(service_name="comments", input_key="demo", tech_results=[])],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        result_by_index = iter(results)
        augmented = []
        for item in top_n:
            augmented.append(self._item_with_surrogate(item, result_by_index))
        return augmented

    def _item_with_surrogate(self, item: object, result_by_index: object) -> object:
        """Merge the next batch result into the matching input item.

        Batch services preserve order, so the stage can combine results without storing temporary IDs.

        Args:
            item: Single source item, database row, or registry entry being transformed.
            result_by_index: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _item_with_surrogate(
                    item={"title": "Example", "url": "https://youtu.be/demo"},
                    result_by_index=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                "AI safety"
        """
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
        """Extract the text surrogate payload from a successful service result.

        Downstream stages can read the same fields regardless of which source text was available.

        Args:
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _surrogate_from_result(
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                "AI safety"
        """
        return first_tech_output(result, dict, require_success=True, require_truthy=True)

    def _items_with_summaries(self, augmented: list, summary_results: list) -> list:
        """Attach generated summaries to items in their original batch order.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            augmented: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
            summary_results: Summary results value that changes the behavior described by this
                             helper.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _items_with_summaries(
                    augmented=[[1.0, 2.0], [3.0, 4.0]],
                    summary_results=["AI safety"],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        result_by_index = iter(summary_results)
        enriched: list[dict] = []
        for item in augmented:
            enriched.append(self._item_with_summary(item, result_by_index))
        return enriched

    def _item_with_summary(self, item: object, result_by_index: object) -> object:
        """Merge one summary result into the matching source item.

        Downstream stages can read the same fields regardless of which source text was available.

        Args:
            item: Single source item, database row, or registry entry being transformed.
            result_by_index: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _item_with_summary(
                    item={"title": "Example", "url": "https://youtu.be/demo"},
                    result_by_index=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                "AI safety"
        """
        if not isinstance(item, dict):
            return item
        merged = self._summary_from_result(next(result_by_index))
        return merged if isinstance(merged, dict) else dict(item)

    def _summary_from_result(self, result: object) -> object:
        """Extract the summary payload from a successful service result.

        Downstream stages can read the same fields regardless of which source text was available.

        Args:
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _summary_from_result(
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                "AI safety"
        """
        return first_tech_output(result, dict)
