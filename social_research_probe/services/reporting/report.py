"""Report writing service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService


class ReportService(BaseService):
    """Write final report to disk (HTML + Markdown fallback).

    Input: dict with 'report' and optional 'allow_html' keys.
    """

    service_name: ClassVar[str] = "youtube.reporting.report"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.html"

    def _get_technologies(self):
        from social_research_probe.technologies.report_render import HtmlRenderTech

        return [HtmlRenderTech()]

    async def write_report(self, report: dict, *, allow_html: bool = True) -> str:
        """Write report and return access path or command.

        Falls back to Markdown when HTML is disabled or fails.
        """
        from social_research_probe.services.reporting import write_final_report

        return write_final_report(report, allow_html=allow_html)
