"""LLM summary enrichment service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class SummaryService(BaseService):
    """Generate LLM summaries for enriched video items.

    Input per item: a ScoredItem dict.
    Delegates to llm/ensemble.py multi_llm_prompt for the actual generation.
    """

    service_name: ClassVar[str] = "youtube.enriching.summary"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.summary"

    def _get_technologies(self, cfg):
        return []

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Generate summary for one ScoredItem via LLM ensemble."""
        from social_research_probe.llm.ensemble import multi_llm_prompt

        title = data.get("title", "") if isinstance(data, dict) else ""
        transcript = data.get("transcript", "") if isinstance(data, dict) else ""
        word_limit = 200
        prompt = (
            f"Summarise this YouTube video in at most {word_limit} words.\n"
            f"Title: {title}\nTranscript: {transcript[:3000]}"
        )
        try:
            summary = await multi_llm_prompt(prompt) or ""
            tr = TechResult(tech_name="llm_ensemble", input=data, output=summary, success=bool(summary))
        except Exception as exc:
            tr = TechResult(tech_name="llm_ensemble", input=data, output=None, success=False, error=str(exc))
        return ServiceResult(service_name=self.service_name, input_key=title, tech_results=[tr])
