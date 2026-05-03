"""HTML report generation service (synchronous; runs after all pipeline stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.report_render import HtmlRenderTech


class HtmlReportService(BaseService):
    """Generate and write the HTML research report.

    Synchronous — runs after all pipeline stages complete. Input: dict with report, data_dir, and
    report config keys.

    Examples:
        Input:
            HtmlReportService
        Output:
            HtmlReportService
    """

    service_name: ClassVar[str] = "youtube.reporting.html"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.html"

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
        return [HtmlRenderTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the HTML report service result.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

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
        result.input_key = "report"
        return result
