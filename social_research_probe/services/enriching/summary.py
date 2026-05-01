"""LLM summary enrichment service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.enriching import SummaryEnsembleTech


def _configured_word_limit() -> int:
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    try:
        limit = int(cfg.tunables.get("per_item_summary_words", 100))
    except (AttributeError, TypeError, ValueError):
        return 100
    return limit if limit > 0 else 100


def _with_summary_word_limit(data: object) -> object:
    if not isinstance(data, dict):
        return data
    enriched = dict(data)
    enriched.setdefault("summary_word_limit", _configured_word_limit())
    return enriched


class SummaryService(BaseService):
    """Generate LLM summaries for enriched video items.

    Input per item: a ScoredItem dict.
    Delegates to llm/ensemble.py multi_llm_prompt for the actual generation.
    """

    service_name: ClassVar[str] = "youtube.enriching.summary"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.summary"

    def _get_technologies(self):
        return [SummaryEnsembleTech()]

    def _technology_input(self, data: object) -> object:
        return _with_summary_word_limit(data)

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
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
