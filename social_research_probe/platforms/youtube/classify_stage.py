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

    Runs between fetch and score so downstream stages read a meaningful
    ``source_class`` instead of a hardcoded ``"unknown"``. Falls back to
    ``"unknown"`` when the service gate is off or the chosen provider
    returns no signal so the report still renders.
    """

    @property
    def stage_name(self) -> str:
        return "classify"

    async def _classify(self, items: list) -> list[dict]:
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
        from social_research_probe.services.classifying.source_class import SourceClassService

        results = await SourceClassService().execute_batch(pending)
        return {
            channel: self._output_class(result)
            for channel, result in zip(pending_channels, results, strict=True)
        }

    def _output_class(self, result: object) -> str:
        from social_research_probe.utils.core.classifying import coerce_class

        for tr in getattr(result, "tech_results", []):
            if tr.success and isinstance(tr.output, dict):
                return coerce_class(tr.output.get("source_class"))
        return "unknown"

    def _store_passthrough(self, state: PipelineState, raw_items: list) -> PipelineState:
        state.set_stage_output("classify", {"items": raw_items})
        return state

    def _store_classified(
        self, state: PipelineState, fetch: dict, classified: list[dict]
    ) -> PipelineState:
        fetch["items"] = classified
        state.set_stage_output("fetch", fetch)
        state.set_stage_output("classify", {"items": classified})
        return state

    async def execute(self, state: PipelineState) -> PipelineState:
        fetch = state.get_stage_output("fetch")
        raw_items = list(fetch.get("items", []))

        if not self._is_enabled(state) or not raw_items:
            return self._store_passthrough(state, raw_items)

        classified = await self._classify(raw_items)
        return self._store_classified(state, fetch, classified)
