"""SQLite persistence service: writes a completed research run to srp.db."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult


class PersistenceService(BaseService[dict, dict]):
    """Persist a completed research run to the local SQLite database.

    Input: dict with 'report', 'db_path', 'config' keys. Output: TechResult.output is dict with
    db_path, run_pk, run_id, counts.

    Examples:
        Input:
            PersistenceService
        Output:
            PersistenceService
    """

    service_name: ClassVar[str] = "persistence"
    enabled_config_key: ClassVar[str] = "services.persistence.sqlite"
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
        from social_research_probe.technologies.persistence.sqlite import SQLitePersistTech

        return [SQLitePersistTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the persistence service result.

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
        output = await tech.execute(input_data)
        return ServiceResult(
            service_name=self.service_name,
            input_key="persist",
            tech_results=[
                TechResult(
                    tech_name=tech.name,
                    input=input_data,
                    output=output,
                    success=output is not None,
                )
            ],
        )
