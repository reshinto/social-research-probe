"""HTML report generation service (synchronous; runs after all pipeline stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class HtmlReportService(BaseService):
    """Generate and write the HTML research report.

    Synchronous — runs after all pipeline stages complete.
    Input: dict with packet, data_dir, and report config keys.
    """

    service_name: ClassVar[str] = "youtube.reporting.html"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.html"

    def _get_technologies(self, cfg):
        return []

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Write HTML report; data must have 'packet' and 'data_dir' keys."""
        import asyncio

        from social_research_probe.technologies.report_render.html.raw_html.youtube import (
            write_html_report,
        )

        packet = data.get("packet") if isinstance(data, dict) else data
        data_dir = data.get("data_dir") if isinstance(data, dict) else None
        try:
            html_path = await asyncio.to_thread(write_html_report, packet, data_dir)
            tr = TechResult(tech_name="html_render", input=data, output=html_path, success=True)
        except Exception as exc:
            tr = TechResult(tech_name="html_render", input=data, output=None, success=False, error=str(exc))
        return ServiceResult(service_name=self.service_name, input_key="packet", tech_results=[tr])
