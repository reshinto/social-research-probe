"""Narrative clustering service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.narratives import NarrativeClustererTech


class NarrativeClusteringService(BaseService):
    """Cluster claims into narrative groups via entity co-occurrence.

    Input: dict with 'items' key containing pipeline items with extracted_claims.

    Examples:
        Input:
            NarrativeClusteringService
        Output:
            NarrativeClusteringService
    """

    service_name: ClassVar[str] = "youtube.analyzing.narratives"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.narratives"

    def _get_technologies(self):
        """Return the narrative clustering technology adapter.

        Returns:
            List containing the NarrativeClustererTech instance.

        Examples:
            Input:
                _get_technologies()
            Output:
                [NarrativeClustererTech()]
        """
        return [NarrativeClustererTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Pass through technology results.

        Args:
            data: Input payload at this service boundary.
            result: ServiceResult with tech_results from the technology run.

        Returns:
            ServiceResult unchanged (technology output is the final output).

        Examples:
            Input:
                await execute_service(data={}, result=ServiceResult())
            Output:
                ServiceResult()
        """
        return result
