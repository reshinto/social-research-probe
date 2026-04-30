"""Item scoring service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService
from social_research_probe.technologies.scoring import ScoringComputeTech


class ScoringService(BaseService):
    """Score and rank research items using trust/trend/opportunity signals.

    Delegates to scoring/compute.py via ScoringComputeTech.
    """

    service_name: ClassVar[str] = "youtube.scoring.score"
    enabled_config_key: ClassVar[str] = "services.youtube.scoring.score"

    def _get_technologies(self):
        return [ScoringComputeTech()]

    async def score_and_rank(
        self,
        items: list,
        engagement_metrics: list,
        weights,
        limit: int,
    ) -> dict:
        """Score items and return ranked output dict.

        Returns {"all_scored": items, "top_n": items[:limit]} if disabled or empty.
        """
        if not self.is_enabled() or not items:
            return {"all_scored": items, "top_n": items[:limit]}
        data = {
            "items": items,
            "engagement_metrics": engagement_metrics,
            "weights": weights,
        }
        result = await self.execute_one(data)
        scored = []
        for tr in result.tech_results:
            if tr.success and isinstance(tr.output, list):
                scored = tr.output
                break
        return {"all_scored": scored, "top_n": scored[:limit]}
