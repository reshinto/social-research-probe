"""Export artifact writing service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult


class ExportService(BaseService):
    """Write export artifacts (CSV, markdown, JSON) alongside the HTML report.

    Input: dict with 'report', 'config', 'stem', 'reports_dir' keys. Output: TechResult.output is
    dict[str, str] of artifact name → path.

    Examples:
        Input:
            ExportService
        Output:
            ExportService
    """

    service_name: ClassVar[str] = "youtube.reporting.export"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.export"
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
        from social_research_probe.technologies.report_render.export import ExportPackageTech

        return [ExportPackageTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the export service result.

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
        input_data = data if isinstance(data, dict) else {}
        tech = self._get_technologies()[0]
        tech.caller_service = self.service_name
        paths = await tech.execute(input_data) or {}
        return ServiceResult(
            service_name=self.service_name,
            input_key="export",
            tech_results=[
                TechResult(
                    tech_name=tech.name,
                    input=input_data,
                    output=paths,
                    success=isinstance(paths, dict),
                )
            ],
        )
