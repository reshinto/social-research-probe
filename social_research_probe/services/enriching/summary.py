"""LLM summary enrichment service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.enriching import SummaryEnsembleTech


def _configured_word_limit() -> int:
    """Read the configured summary word limit.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            _configured_word_limit()
        Output:
            5
    """
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    try:
        limit = int(cfg.tunables.get("per_item_summary_words", 100))
    except (AttributeError, TypeError, ValueError):
        return 100
    return limit if limit > 0 else 100


def _with_summary_word_limit(data: object) -> object:
    """Attach the configured summary word limit before sending text to the summarizer.

    Downstream stages can read the same fields regardless of which source text was available.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _with_summary_word_limit(
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            "AI safety"
    """
    if not isinstance(data, dict):
        return data
    enriched = dict(data)
    enriched.setdefault("summary_word_limit", _configured_word_limit())
    return enriched


class SummaryService(BaseService):
    """Generate LLM summaries for enriched video items.

    Input per item: a ScoredItem dict. Delegates to llm/ensemble.py multi_llm_prompt for the actual
    generation.

    Examples:
        Input:
            SummaryService
        Output:
            SummaryService
    """

    service_name: ClassVar[str] = "youtube.enriching.summary"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.summary"

    def _get_technologies(self):
        """Return the technology adapters this service should run.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _get_technologies()
            Output:
                "AI safety"
        """
        return [SummaryEnsembleTech()]

    def _technology_input(self, data: object) -> object:
        """Shape the service payload before it is sent to a technology adapter.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _technology_input(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        return _with_summary_word_limit(data)

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the summary service result.

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
        title = data.get("title", "") if isinstance(data, dict) else repr(data)
        summary = next(
            (tr.output for tr in result.tech_results if tr.success and tr.output),
            None,
        )
        if isinstance(data, dict):
            if summary:
                merged = {**data, "summary": summary, "one_line_takeaway": summary}
                surr = data.get("text_surrogate")
                if isinstance(surr, dict) and surr.get("primary_text_source"):
                    # Record the source that produced the summary so renderers can flag
                    # metadata-only summaries instead of presenting them as transcript-backed.
                    merged["summary_source"] = surr["primary_text_source"]
            else:
                merged = dict(data)
            if result.tech_results:
                result.tech_results[0].output = merged
                result.tech_results[0].success = bool(summary)
        result.input_key = title
        return result
