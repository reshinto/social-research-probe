"""YouTubeClassifyStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.pipeline.helpers import (
    apply_channel_classes,
    resolve_item_source_class,
)


class YouTubeClassifyStage(BaseStage):
    """Classify each fetched item's channel into a source_class enum value.

    Runs between fetch and score so downstream stages read a meaningful ``source_class`` instead of
    a hardcoded ``"unknown"``. Falls back to ``"unknown"`` when the service gate is off or the
    chosen provider returns no signal so the report still renders.

    Examples:
        Input:
            YouTubeClassifyStage
        Output:
            YouTubeClassifyStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `classify` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "classify"
        """
        return "classify"

    async def _classify(self, items: list) -> list[dict]:
        """Document the classify rule at the boundary where callers use it.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            items: Ordered source items being carried through the current pipeline step.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _classify(
                    items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        from social_research_probe.utils.pipeline.helpers import normalize_item

        normalized = [d for d in (normalize_item(it) for it in items) if d is not None]
        if not normalized:
            return list(items)
        classified, pending, pending_channels = self._build_classification_partition(normalized)
        if pending:
            channel_classes = await self._fetch_channel_classes(pending, pending_channels)
            apply_channel_classes(classified, channel_classes)
        return classified

    def _build_classification_partition(
        self, normalized: list[dict]
    ) -> tuple[list[dict], list[dict], list[str]]:
        """Build the classification partition structure consumed by the next step.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            normalized: Normalized source-class label after provider output coercion.

        Returns:
            Tuple whose positions are part of the public helper contract shown in the example.

        Examples:
            Input:
                _build_classification_partition(
                    normalized=["AI safety"],
                )
            Output:
                ["AI safety", "model evaluation"]
        """
        classified: list[dict] = []
        pending: list[dict] = []
        pending_channels: list[str] = []
        pending_seen: set[str] = set()
        for item in normalized:
            channel = str(item.get("channel") or item.get("author_name") or "")
            enriched = resolve_item_source_class(item)
            classified.append(enriched)
            if enriched.get("source_class") == "unknown" and channel not in pending_seen:
                pending.append(item)
                pending_channels.append(channel)
                pending_seen.add(channel)
        return classified, pending, pending_channels

    async def _fetch_channel_classes(
        self, pending: list[dict], pending_channels: list[str]
    ) -> dict[str, str]:
        """Fetch channel classes without exposing provider details to callers.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            pending: Intermediate collection used to preserve ordering while stage results are merged.
            pending_channels: Intermediate collection used to preserve ordering while stage results are
                              merged.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _fetch_channel_classes(
                    pending=[],
                    pending_channels=[],
                )
            Output:
                {"enabled": True}
        """
        from social_research_probe.services.classifying.source_class import SourceClassService

        results = await SourceClassService().execute_batch(pending)
        return {
            channel: self._output_class(result)
            for channel, result in zip(pending_channels, results, strict=True)
        }

    def _output_class(self, result: object) -> str:
        """Return the output class.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Examples:
            Input:
                _output_class(
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                "AI safety"
        """
        from social_research_probe.utils.core.classifying import coerce_class

        for tr in getattr(result, "tech_results", []):
            if tr.success and isinstance(tr.output, dict):
                return coerce_class(tr.output.get("source_class"))
        return "unknown"

    def _store_passthrough(self, state: PipelineState, raw_items: list) -> PipelineState:
        """Build the small payload that carries items through this workflow.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.
            raw_items: Ordered source items being carried through the current pipeline step.

        Returns:
            The same PipelineState instance after this stage has published its output.

        Examples:
            Input:
                _store_passthrough(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                    raw_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                PipelineState(platform_type="youtube", cmd=None, cache=None)
        """
        state.set_stage_output("classify", {"items": raw_items})
        return state

    def _store_classified(
        self, state: PipelineState, fetch: dict, classified: list[dict]
    ) -> PipelineState:
        """Build the small payload that carries items through this workflow.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.
            fetch: Intermediate collection used to preserve ordering while stage results are merged.
            classified: Intermediate collection used to preserve ordering while stage results are
                        merged.

        Returns:
            The same PipelineState instance after this stage has published its output.

        Examples:
            Input:
                _store_classified(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                    fetch=[],
                    classified=[],
                )
            Output:
                PipelineState(platform_type="youtube", cmd=None, cache=None)
        """
        fetch["items"] = classified
        state.set_stage_output("fetch", fetch)
        state.set_stage_output("classify", {"items": classified})
        return state

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube classify stage and publish its PipelineState output.

        The YouTube classify stage reads the state built so far and publishes the smallest output later
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
        raw_items = list(fetch.get("items", []))

        if not self._is_enabled(state) or not raw_items:
            return self._store_passthrough(state, raw_items)

        classified = await self._classify(raw_items)
        return self._store_classified(state, fetch, classified)
