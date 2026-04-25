"""Item scoring service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class ScoringService(BaseService):
    """Score and rank research items using trust/trend/opportunity signals.

    Pure computation — no I/O technologies. Delegates to scoring/combine.py.
    """

    service_name: ClassVar[str] = "youtube.scoring.score"
    enabled_config_key: ClassVar[str] = "services.youtube.scoring.score"

    def _get_technologies(self):
        return []

    async def execute_one(self, data: object) -> ServiceResult:
        """Score a list of raw items; data is dict with 'items' and 'weights' keys."""
        from social_research_probe.technologies.scoring.combine import overall_score

        items = data.get("items", []) if isinstance(data, dict) else []
        weights = data.get("weights", {}) if isinstance(data, dict) else {}
        try:
            scored = [
                {
                    **item,
                    "overall_score": overall_score(
                        trust=item.get("trust", 0.0),
                        trend=item.get("trend", 0.0),
                        opportunity=item.get("opportunity", 0.0),
                        weights=weights or None,
                    ),
                }
                for item in items
                if isinstance(item, dict)
            ]
            tr = TechResult(tech_name="scoring.combine", input=data, output=scored, success=True)
        except Exception as exc:
            tr = TechResult(
                tech_name="scoring.combine", input=data, output=None, success=False, error=str(exc)
            )
        return ServiceResult(service_name=self.service_name, input_key="items", tech_results=[tr])
