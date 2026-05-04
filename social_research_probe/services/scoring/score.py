"""Item scoring service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.scoring import ScoringComputeTech


class ScoringService(BaseService):
    """Score and rank research items using trust/trend/opportunity signals.

    Delegates to scoring/compute.py via ScoringComputeTech.

    Examples:
        Input:
            ScoringService
        Output:
            ScoringService
    """

    service_name: ClassVar[str] = "youtube.scoring.score"
    enabled_config_key: ClassVar[str] = "services.youtube.scoring.score"

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
        return [ScoringComputeTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the scoring service result.

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
        limit = int(data.get("limit", 0)) if isinstance(data, dict) else 0
        scored = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, list)),
            [],
        )
        output = {"all_scored": scored, "top_n": scored[:limit] if limit else scored}
        if result.tech_results:
            result.tech_results[0].output = output
        return result
