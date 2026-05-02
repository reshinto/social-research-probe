"""Export artifact writing service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult


class ExportService(BaseService):
    """Write export artifacts (CSV, markdown, JSON) alongside the HTML report.

    Input: dict with 'report', 'config', 'stem', 'reports_dir' keys.
    Output: TechResult.output is dict[str, str] of artifact name → path.
    """

    service_name: ClassVar[str] = "youtube.reporting.export"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.export"
    run_technologies_concurrently: ClassVar[bool] = False

    def _get_technologies(self):
        from social_research_probe.technologies.report_render.export import ExportPackageTech

        return [ExportPackageTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
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
