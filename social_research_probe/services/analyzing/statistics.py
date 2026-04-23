"""Statistical analysis service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class StatisticsService(BaseService):
    """Run statistical analysis on scored research items.

    Input: dict with 'scored_items' key containing list of ScoredItem.
    Delegates to technologies/statistics/selector.py select_and_run.
    """

    service_name: ClassVar[str] = "youtube.analyzing.statistics"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.statistics"

    def _get_technologies(self, cfg):
        return []

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Run stats analysis on scored_items from data dict."""
        import asyncio

        from social_research_probe.technologies.statistics.selector import select_and_run

        scored_items = data.get("scored_items", []) if isinstance(data, dict) else []
        scores = [
            item.get("overall_score", 0.0)
            for item in scored_items
            if isinstance(item, dict)
        ]
        try:
            stats_results = await asyncio.to_thread(select_and_run, scores, "overall_score")
            tr = TechResult(tech_name="stats_selector", input=data, output=stats_results, success=True)
        except Exception as exc:
            tr = TechResult(tech_name="stats_selector", input=data, output=None, success=False, error=str(exc))
        return ServiceResult(service_name=self.service_name, input_key="scored_items", tech_results=[tr])
