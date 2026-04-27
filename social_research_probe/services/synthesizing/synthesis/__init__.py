"""Research synthesis service: generate final LLM synthesis from all stage outputs."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.synthesizing import SynthesisTech


class SynthesisService(BaseService):
    """Generate final research synthesis from stage outputs.

    Input: dict with research context (top_n, stats_results, chart_results, etc.).
    Uses synthesize/llm_contract.py build_synthesis_prompt + LLM ensemble call.
    """

    service_name: ClassVar[str] = "youtube.synthesizing.synthesis"
    enabled_config_key: ClassVar[str] = "services.youtube.synthesizing.synthesis"

    def _get_technologies(self):
        return [SynthesisTech()]

    async def execute_one(self, data: object) -> ServiceResult:
        result = await super().execute_one(data)
        result.input_key = "context"
        return result
