"""YouTubeClaimsStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.pipeline.helpers import dict_items, first_tech_output


class YouTubeClaimsStage(BaseStage):
    """Extract structured claims from top-N items.

    Examples:
        Input:
            YouTubeClaimsStage
        Output:
            YouTubeClaimsStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `claims` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "claims"
        """
        return "claims"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube claims stage and publish its PipelineState output.

        The YouTube claims stage reads the state built so far and publishes the smallest output later
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
        """Document the items with claims rule at the boundary where callers use it.

        Extraction, review, corroboration, and reporting all need the same claim shape.

        Args:
            top_n: Ordered source items being carried through the current pipeline step.
            results: Service or technology result being inspected for payload and diagnostics.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _items_with_claims(
                    top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    results=[ServiceResult(service_name="comments", input_key="demo", tech_results=[])],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        result_iter = iter(results)
        enriched = []
        for item in top_n:
            enriched.append(self._item_with_claims(item, result_iter))
        return enriched

    def _item_with_claims(self, item: object, result_iter: object) -> object:
        """Extract the first successful payload from a ServiceResult.

        This keeps ServiceResult parsing out of stages, where missing and failed outputs should look the
        same.

        Args:
            item: Single source item, database row, or registry entry being transformed.
            result_iter: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _item_with_claims(
                    item={"title": "Example", "url": "https://youtu.be/demo"},
                    result_iter=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                "AI safety"
        """
        if not isinstance(item, dict):
            return item
        merged = first_tech_output(next(result_iter), dict)
        return merged if isinstance(merged, dict) else {**item, "extracted_claims": []}
