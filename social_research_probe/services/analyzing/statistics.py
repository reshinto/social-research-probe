"""Statistical analysis service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.statistics import (
    StatisticsTech,
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

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        result.input_key = "scored_items"
        return result
