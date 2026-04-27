"""Item scoring service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService
from social_research_probe.technologies.base import BaseTechnology


class ScoringComputeTech(BaseTechnology[object, list]):
    """Technology wrapper for computing full scores for a batch of items."""

    name: ClassVar[str] = "scoring.compute"

    async def _execute(self, input_data: object) -> list:
        from social_research_probe.services.scoring.compute import score_items

        items = input_data.get("items", []) if isinstance(input_data, dict) else []
        metrics = input_data.get("engagement_metrics", []) if isinstance(input_data, dict) else []
        weights = input_data.get("weights", {}) if isinstance(input_data, dict) else None
        return score_items(items, metrics, weights)


class ScoringService(BaseService):
    """Score and rank research items using trust/trend/opportunity signals.

    Delegates to scoring/compute.py via ScoringComputeTech.
    """

    service_name: ClassVar[str] = "youtube.scoring.score"
    enabled_config_key: ClassVar[str] = "services.youtube.scoring.score"

    def _get_technologies(self):
        return [ScoringComputeTech()]
