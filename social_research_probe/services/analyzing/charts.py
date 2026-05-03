"""Chart generation service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.charts import (
    ChartsTech,
)

_INPUT_KEY = "scored_items"


class ChartsService(BaseService):
    """Render the full chart suite from scored items.

    Input: dict with 'scored_items' key.

    Examples:
        Input:
            ChartsService
        Output:
            ChartsService
    """

    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"

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
        return [ChartsTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the charts service result.

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
        chart_outputs = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, list)),
            [],
        )
        charts = {
            "chart_outputs": chart_outputs,
            "chart_captions": [c.caption for c in chart_outputs],
            "chart_takeaways": [],
        }
        if result.tech_results:
            result.tech_results[0].output = charts
        result.input_key = _INPUT_KEY
        return result
