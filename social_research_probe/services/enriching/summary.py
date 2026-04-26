"""LLM summary enrichment service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult
from social_research_probe.utils.display.progress import log_with_time


class SummaryService(BaseService):
    """Generate LLM summaries for enriched video items.

    Input per item: a ScoredItem dict.
    Delegates to llm/ensemble.py multi_llm_prompt for the actual generation.
    """

    service_name: ClassVar[str] = "youtube.enriching.summary"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.summary"

    def _get_technologies(self):
        return []

    @log_with_time("[srp] {self.service_name}: execute_one")
    async def execute_one(self, data: object) -> ServiceResult:
        """Generate summary for one ScoredItem via LLM ensemble."""
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
        try:
            summary = get_str(summary_cache(), cache_key)
            if summary is None:
                summary = await multi_llm_prompt(prompt) or ""
                set_str(summary_cache(), cache_key, summary, input_key=prompt)
            tr = TechResult(
                tech_name="llm_ensemble", input=data, output=summary, success=bool(summary)
            )
        except Exception as exc:
            tr = TechResult(
                tech_name="llm_ensemble", input=data, output=None, success=False, error=str(exc)
            )
        return ServiceResult(service_name=self.service_name, input_key=title, tech_results=[tr])
