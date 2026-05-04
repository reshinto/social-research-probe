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

from social_research_probe.services import BaseService, ServiceResult
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
    """Return the configured classifier provider, defaulting to ``"hybrid"``.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            resolve_provider_name()
        Output:
            "brave"
    """
    from social_research_probe.config import load_active_config

    raw = load_active_config().raw.get("services", {}).get("youtube", {}).get("classifying", {})
    provider = str(raw.get("provider", "hybrid")).lower()
    return provider if provider in _PROVIDER_MAP else "hybrid"


class SourceClassService(BaseService[dict, str]):
    """Classify one item's channel into a source_class enum value.

    Implements the standard ``BaseService`` contract: ``_get_technologies`` returns the single
    classifier selected by config, and ``execute_one`` runs it through the BaseService timing/error
    path.

    Examples:
        Input:
            SourceClassService
        Output:
            SourceClassService
    """

    service_name: ClassVar[str] = "youtube.classifying.source_class"
    enabled_config_key: ClassVar[str] = "services.youtube.classifying.source_class"

    def _get_technologies(self) -> list[ClassifierTech]:
        """Return the technology adapters this service is allowed to run.

        Services turn platform items into adapter requests and normalize results so stages handle
        success, skip, and failure the same way.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _get_technologies()
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        return [_PROVIDER_MAP[resolve_provider_name()]()]

    async def execute_service(self, data: dict, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the source class service result.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_service(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
        from social_research_probe.utils.core.classifying import (
            classify_by_title_signal,
            coerce_class,
        )
        from social_research_probe.utils.pipeline.helpers import normalize_item

        item = normalize_item(data)
        if item is None:
            return result
        existing = coerce_class(item.get("source_class"))
        resolved = next(
            (
                coerce_class(tr.output)
                for tr in result.tech_results
                if tr.success and isinstance(tr.output, str)
            ),
            "unknown",
        )
        source_class = existing if existing != "unknown" else resolved
        if classify_by_title_signal(str(item.get("title") or "")) == "commentary":
            source_class = "commentary"
        output = {**item, "source_class": source_class}
        if result.tech_results:
            result.tech_results[0].output = output
            result.tech_results[0].success = True
        return result
