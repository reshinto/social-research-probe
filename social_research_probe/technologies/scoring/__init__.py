from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class ScoringComputeTech(BaseTechnology[object, list]):
    """Technology wrapper for computing full scores for a batch of items."""

    name: ClassVar[str] = "scoring.compute"

    async def _execute(self, input_data: object) -> list:
        from social_research_probe.services.scoring import score_items

        items = input_data.get("items", []) if isinstance(input_data, dict) else []
        metrics = input_data.get("engagement_metrics", []) if isinstance(input_data, dict) else []
        weights = input_data.get("weights", {}) if isinstance(input_data, dict) else None
        return score_items(items, metrics, weights)
