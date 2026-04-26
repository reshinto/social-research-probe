"""LLM summary enrichment service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult
from social_research_probe.technologies.base import BaseTechnology


class SummaryEnsembleTech(BaseTechnology[object, str]):
    """Technology using the LLM ensemble to generate summaries."""

    name: ClassVar[str] = "llm_ensemble"

    async def _execute(self, data: object) -> str | None:
        from social_research_probe.services.llm.ensemble import multi_llm_prompt
        from social_research_probe.utils.caching.pipeline_cache import (
            get_str,
            hash_key,
            set_str,
            summary_cache,
        )

        title = data.get("title", "") if isinstance(data, dict) else ""
        url = data.get("url", "") if isinstance(data, dict) else ""
        transcript = data.get("transcript", "") if isinstance(data, dict) else ""
        word_limit = 200
        prompt = (
            f"Summarise this YouTube video in at most {word_limit} words.\n"
            f"Title: {title}\nTranscript: {transcript[:3000]}"
        )
        cache_key = hash_key(str(url or title), prompt)

        summary = get_str(summary_cache(), cache_key)
        if summary is None:
            summary = await multi_llm_prompt(prompt) or ""
            set_str(summary_cache(), cache_key, summary, input_key=prompt)

        return summary if summary else None


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
        result = await super().execute_one(data)
        title = data.get("title", "") if isinstance(data, dict) else repr(data)
        result.input_key = title
        return result
