"""Research synthesis service: generate final LLM synthesis from all stage outputs."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class SynthesisService(BaseService):
    """Generate final research synthesis from stage outputs.

    Input: dict with research context (top_n, stats_results, chart_results, etc.).
    Uses synthesize/llm_contract.py build_synthesis_prompt + LLM ensemble call.
    """

    service_name: ClassVar[str] = "youtube.synthesizing.synthesis"
    enabled_config_key: ClassVar[str] = "services.youtube.synthesizing.synthesis"

    def _get_technologies(self, cfg):
        return []

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Generate synthesis from the research context in data."""
        from social_research_probe.services.llm.ensemble import multi_llm_prompt
        from social_research_probe.services.synthesizing.llm_contract import build_synthesis_prompt

        try:
            prompt = build_synthesis_prompt(data if isinstance(data, dict) else {})
            synthesis = await multi_llm_prompt(prompt) or ""
            tr = TechResult(tech_name="llm_synthesis", input=data, output=synthesis, success=bool(synthesis))
        except Exception as exc:
            tr = TechResult(tech_name="llm_synthesis", input=data, output=None, success=False, error=str(exc))
        return ServiceResult(service_name=self.service_name, input_key="context", tech_results=[tr])
