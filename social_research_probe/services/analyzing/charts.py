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

    async def execute_one(self, data: object) -> ServiceResult:
        result = await super().execute_one(data)
        result.input_key = _INPUT_KEY
        return result

    async def render_charts(self, items: list) -> dict:
        """Render chart suite for items.

        Returns {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []} if disabled.
        """
        if not self.is_enabled():
            return {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []}
        result = await self.execute_one({"scored_items": items})
        chart_outputs = []
        for tr in result.tech_results:
            if tr.success and isinstance(tr.output, list):
                chart_outputs = tr.output
                break
        return {
            "chart_outputs": chart_outputs,
            "chart_captions": [c.caption for c in chart_outputs],
            "chart_takeaways": [],
        }
