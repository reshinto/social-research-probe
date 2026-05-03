"""Research synthesis service: generate final LLM synthesis from all stage outputs."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.synthesizing import SynthesisTech


class SynthesisService(BaseService):
    """Generate final research synthesis from stage outputs.

    Input: dict with research context (top_n, stats_results, chart_results, etc.). Uses
    synthesize/llm_contract.py build_synthesis_prompt + LLM ensemble call.

    Examples:
        Input:
            SynthesisService
        Output:
            SynthesisService
    """

    service_name: ClassVar[str] = "youtube.synthesizing.synthesis"
    enabled_config_key: ClassVar[str] = "services.youtube.synthesizing.synthesis"

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
        return [SynthesisTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the synthesis service result.

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
        result.input_key = "context"
        return result
