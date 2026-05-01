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

    async def execute_one(self, data: object) -> ServiceResult:
        payload = _with_summary_word_limit(data)
        result = await super().execute_one(payload)
        title = data.get("title", "") if isinstance(data, dict) else repr(data)
        result.input_key = title
        return result

    async def enrich_batch(self, top_n: list) -> list[dict]:
        """Generate summaries and merge into items. Returns enriched item list."""
        results = await self.execute_batch(top_n)
        enriched: list[dict] = []
        for item, r in zip(top_n, results, strict=True):
            s = next(
                (tr.output for tr in r.tech_results if tr.success and tr.output),
                None,
            )
            if s:
                merged = {**item, "summary": s, "one_line_takeaway": s}
                surr = item.get("text_surrogate")
                if isinstance(surr, dict) and surr.get("primary_text_source"):
                    merged["summary_source"] = surr["primary_text_source"]
                enriched.append(merged)
            else:
                enriched.append(dict(item))
        return enriched
