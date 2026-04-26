"""HTML report generation service (synchronous; runs after all pipeline stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class HtmlReportService(BaseService):
    """Generate and write the HTML research report.

    Synchronous — runs after all pipeline stages complete.
    Input: dict with report, data_dir, and report config keys.
    """

    service_name: ClassVar[str] = "youtube.reporting.html"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.html"

    def _get_technologies(self):
        return []

    async def execute_one(self, data: object) -> ServiceResult:
        """Write HTML report; data must have a 'report' key."""
        import asyncio

        from social_research_probe.technologies.report_render.html.raw_html.youtube import (
            write_html_report,
        )

        report = data.get("report") if isinstance(data, dict) else data
        try:
            html_path = await asyncio.to_thread(write_html_report, report)
            tr = TechResult(tech_name="html_render", input=data, output=html_path, success=True)
        except Exception as exc:
            tr = TechResult(
                tech_name="html_render", input=data, output=None, success=False, error=str(exc)
            )
        return ServiceResult(service_name=self.service_name, input_key="report", tech_results=[tr])
