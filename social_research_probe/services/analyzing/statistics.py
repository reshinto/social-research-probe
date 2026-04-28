"""Statistical analysis service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.statistics import (
    StatisticsTech,
    _cached_or_compute,
    _compute,
    _stats_per_target,
    compute_async,
    items_from_data,
)


class StatisticsService(BaseService):
    """Run statistical analysis on scored research items.

    Input: dict with 'scored_items' key containing list of scored item dicts.
    Builds derived target arrays then runs the stats selector per target.
    """

    service_name: ClassVar[str] = "youtube.analyzing.statistics"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.statistics"

    def _get_technologies(self):
        return [StatisticsTech()]

    @staticmethod
    def _items(data: object) -> list[dict]:
        return items_from_data(data)

    @staticmethod
    def _stats_per_target(targets: dict[str, list]) -> dict[str, list]:
        return _stats_per_target(targets)

    @staticmethod
    def _compute(items: list[dict]) -> dict:
        return _compute(items)

    @staticmethod
    def _cached_or_compute(items: list[dict]) -> dict:
        return _cached_or_compute(items)

    @staticmethod
    async def _compute_async(items: list[dict]) -> dict:
        return await compute_async(items)

    async def execute_one(self, data: object) -> ServiceResult:
        result = await super().execute_one(data)
        result.input_key = "scored_items"
        return result
