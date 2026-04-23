"""Chart generation service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class ChartsService(BaseService):
    """Generate charts from statistical results.

    Input: dict with 'stats_results' and 'scored_items' keys.
    Delegates to technologies/charts/selector.py select_and_render.
    """

    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"

    def _get_technologies(self, cfg):
        return []

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Generate charts from scored_items scores in data dict."""
        import asyncio

        from social_research_probe.technologies.charts.selector import select_and_render

        scored_items = data.get("scored_items", []) if isinstance(data, dict) else []
        scores = [
            item.get("overall_score", 0.0)
            for item in scored_items
            if isinstance(item, dict)
        ]
        try:
            chart_result = await asyncio.to_thread(select_and_render, scores, "overall_score")
            tr = TechResult(tech_name="charts_selector", input=data, output=chart_result, success=True)
        except Exception as exc:
            tr = TechResult(tech_name="charts_selector", input=data, output=None, success=False, error=str(exc))
        return ServiceResult(service_name=self.service_name, input_key="stats_results", tech_results=[tr])
