"""Item scoring service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.scoring import ScoringComputeTech


class ScoringService(BaseService):
    """Score and rank research items using trust/trend/opportunity signals.

    Delegates to scoring/compute.py via ScoringComputeTech.
    """

    service_name: ClassVar[str] = "youtube.scoring.score"
    enabled_config_key: ClassVar[str] = "services.youtube.scoring.score"

    def _get_technologies(self):
        return [ScoringComputeTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        limit = int(data.get("limit", 0)) if isinstance(data, dict) else 0
        scored = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, list)),
            [],
        )
        output = {"all_scored": scored, "top_n": scored[:limit] if limit else scored}
        if result.tech_results:
            result.tech_results[0].output = output
        return result
