"""Statistical analysis technology adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


@dataclass
class StatResult:
    """The output of a single statistical analysis."""

    name: str
    value: float
    caption: str


class StatisticsTech(BaseTechnology[object, dict]):
    """Technology wrapper for computing statistics across all targets."""

    name: ClassVar[str] = "stats_per_target"

    async def _execute(self, input_data: object) -> dict:
        from social_research_probe.services.analyzing.statistics import StatisticsService

        return await StatisticsService._compute_async(StatisticsService._items(input_data))
