"""HTML report generation service (synchronous; runs after all pipeline stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies import BaseTechnology


class HtmlRenderTech(BaseTechnology[object, str]):
    """Technology for generating the final HTML report."""

    name: ClassVar[str] = "html_render"

    async def _execute(self, input_data: object) -> str:
        import asyncio

        from social_research_probe.technologies.report_render.html.raw_html.youtube import (
            write_html_report,
        )

        report = input_data.get("report") if isinstance(input_data, dict) else input_data
        return await asyncio.to_thread(write_html_report, report)


class HtmlReportService(BaseService):
    """Generate and write the HTML research report.

    Synchronous — runs after all pipeline stages complete.
    Input: dict with report, data_dir, and report config keys.
    """

    service_name: ClassVar[str] = "youtube.reporting.html"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.html"

    def _get_technologies(self):
        return [HtmlRenderTech()]

    async def execute_one(self, data: object) -> ServiceResult:
        result = await super().execute_one(data)
        result.input_key = "report"
        return result
