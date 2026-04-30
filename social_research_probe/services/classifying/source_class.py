"""Source-class classification service.

Selects a classifier provider (heuristic | llm | hybrid) based on the active
config and exposes it through the standard BaseService contract. The service
itself classifies a single item; per-channel caching, title overrides, and
the disabled-gate fallback are owned by the calling pipeline stage so this
service stays a thin tech wrapper.

Config block::

    [services.youtube.classifying]
    source_class = true       # gate
    provider = "hybrid"       # heuristic | llm | hybrid
"""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService
from social_research_probe.technologies.classifying import (
    HeuristicClassifier,
    HybridClassifier,
    LLMClassifier,
)

ClassifierTech = HeuristicClassifier | LLMClassifier | HybridClassifier

_PROVIDER_MAP: dict[str, type[ClassifierTech]] = {
    "heuristic": HeuristicClassifier,
    "llm": LLMClassifier,
    "hybrid": HybridClassifier,
}


def resolve_provider_name() -> str:
    """Return the configured classifier provider, defaulting to ``"hybrid"``."""
    from social_research_probe.config import load_active_config

    raw = load_active_config().raw.get("services", {}).get("youtube", {}).get("classifying", {})
    provider = str(raw.get("provider", "hybrid")).lower()
    return provider if provider in _PROVIDER_MAP else "hybrid"


class SourceClassService(BaseService[dict, str]):
    """Classify one item's channel into a source_class enum value.

    Implements the standard ``BaseService`` contract: ``_get_technologies``
    returns the single classifier selected by config, and ``execute_one``
    runs it through the BaseService timing/error path.
    """

    service_name: ClassVar[str] = "youtube.classifying.source_class"
    enabled_config_key: ClassVar[str] = "services.youtube.classifying.source_class"

    def _get_technologies(self) -> list[ClassifierTech]:
        return [_PROVIDER_MAP[resolve_provider_name()]()]

    async def classify_batch(self, raw_items: list) -> list[dict]:
        """Normalize, classify, and return enriched items with source_class."""
        from social_research_probe.technologies.classifying import (
            classify_by_title_signal,
            coerce_class,
        )
        from social_research_probe.technologies.scoring import normalize_item

        def _normalize(items: list) -> list[dict]:
            return [d for d in (normalize_item(it) for it in items) if d is not None]

        def _existing_class(item: dict) -> str:
            return coerce_class(item.get("source_class"))

        def _channel_of(item: dict) -> str:
            return str(item.get("channel") or item.get("author_name") or "")

        def _output_class(result) -> str:
            for tr in result.tech_results:
                if tr.success and isinstance(tr.output, str):
                    return coerce_class(tr.output)
            return "unknown"

        def _title_override(item: dict) -> bool:
            return classify_by_title_signal(str(item.get("title") or "")) == "commentary"

        def _enrich(item: dict, base_class: str) -> dict:
            enriched = dict(item)
            enriched["source_class"] = "commentary" if _title_override(item) else base_class
            return enriched

        async def _resolve(item: dict, cache: dict[str, str]) -> str:
            existing = _existing_class(item)
            if existing != "unknown":
                return existing
            channel = _channel_of(item)
            if channel in cache:
                return cache[channel]
            result = await self.execute_one(item)
            resolved = _output_class(result)
            cache[channel] = resolved
            return resolved

        items = _normalize(raw_items)
        if not items:
            return list(raw_items)
        channel_cache: dict[str, str] = {}
        return [_enrich(item, await _resolve(item, channel_cache)) for item in items]
