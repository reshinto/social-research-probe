"""SQLite persistence service: writes a completed research run to srp.db."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult


class PersistenceService(BaseService[dict, dict]):
    """Persist a completed research run to the local SQLite database.

    Input: dict with 'report', 'db_path', 'config' keys.
    Output: TechResult.output is dict with db_path, run_pk, run_id, counts.
    """

    service_name: ClassVar[str] = "persistence"
    enabled_config_key: ClassVar[str] = "services.persistence.sqlite"
    run_technologies_concurrently: ClassVar[bool] = False

    def _get_technologies(self):
        from social_research_probe.technologies.persistence.sqlite import SQLitePersistTech

        return [SQLitePersistTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
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
