"""LLM summary enrichment service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.enriching import SummaryEnsembleTech


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
