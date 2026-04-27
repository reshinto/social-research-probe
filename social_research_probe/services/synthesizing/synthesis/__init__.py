"""Research synthesis service: generate final LLM synthesis from all stage outputs."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult
from social_research_probe.technologies.base import BaseTechnology


class SynthesisTech(BaseTechnology[object, str]):
    """Technology for generating the final research synthesis."""

    name: ClassVar[str] = "llm_synthesis"

    async def _execute(self, input_data: object) -> str | None:
        from social_research_probe.services.llm.ensemble import multi_llm_prompt

        from .llm_contract import build_synthesis_prompt

        prompt = build_synthesis_prompt(input_data if isinstance(input_data, dict) else {})
        synthesis = await multi_llm_prompt(prompt) or ""
        return synthesis if synthesis else None


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
