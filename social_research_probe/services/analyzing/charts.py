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
    """

    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"

    def _get_technologies(self):
        return [ChartsTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
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
