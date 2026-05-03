"""Report writing service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult


class ReportService(BaseService):
    """Write final report to disk (HTML + Markdown fallback).

    Input: dict with 'report' and optional 'allow_html' keys.

    Examples:
        Input:
            ReportService
        Output:
            ReportService
    """

    service_name: ClassVar[str] = "youtube.reporting.report"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.html"
    run_technologies_concurrently: ClassVar[bool] = False

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
        from social_research_probe.technologies.report_render import HtmlRenderTech

        return [HtmlRenderTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Write a report through the standard service lifecycle.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

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
        from social_research_probe.services.reporting import write_final_report

        report = data.get("report", {}) if isinstance(data, dict) else {}
        allow_html = bool(data.get("allow_html", True)) if isinstance(data, dict) else True
        output = write_final_report(report, allow_html=allow_html)
        return ServiceResult(
            service_name=self.service_name,
            input_key="report",
            tech_results=[
                TechResult(
                    tech_name="report_writer",
                    input=data,
                    output=output,
                    success=bool(output),
                )
            ],
        )
