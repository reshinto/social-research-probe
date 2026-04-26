"""Chart generation service."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult
from social_research_probe.utils.display.progress import log_with_time


class ChartsService(BaseService):
    """Generate charts from statistical results.

    Input: dict with 'stats_results' and 'scored_items' keys.
    Delegates to technologies/charts/selector.py select_and_render.
    """

    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"

    def _get_technologies(self):
        return []

    @staticmethod
    def _charts_dir() -> Path:
        """Return the persistent chart output directory for research runs."""
        from social_research_probe.config import load_active_config

        charts_dir = load_active_config().data_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)
        return charts_dir

    @staticmethod
    def _with_path_annotation(chart_result):
        """Add the saved PNG path to the caption shown in Markdown reports."""
        if chart_result is None:
            return None
        annotation = f"_(see PNG: {chart_result.path})_"
        if annotation in chart_result.caption:
            return chart_result
        return replace(chart_result, caption=f"{chart_result.caption}\n{annotation}")

    @log_with_time("[srp] {self.service_name}: execute_one")
    async def execute_one(self, data: object) -> ServiceResult:
        """Generate charts from scored_items scores in data dict."""
        import asyncio

        from social_research_probe.technologies.charts.selector import select_and_render

        scored_items = data.get("scored_items", []) if isinstance(data, dict) else []
        scores = [item.get("overall_score", 0.0) for item in scored_items if isinstance(item, dict)]
        try:
            charts_dir = self._charts_dir()
            chart_result = await asyncio.to_thread(
                select_and_render,
                scores,
                "overall_score",
                str(charts_dir),
            )
            chart_result = self._with_path_annotation(chart_result)
            tr = TechResult(
                tech_name="charts_selector", input=data, output=chart_result, success=True
            )
        except Exception as exc:
            tr = TechResult(
                tech_name="charts_selector", input=data, output=None, success=False, error=str(exc)
            )
        return ServiceResult(
            service_name=self.service_name, input_key="stats_results", tech_results=[tr]
        )
