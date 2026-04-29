"""Chart generation service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.charts import (
    ChartsTech,
    items_from,
)

_INPUT_KEY = "scored_items"


class ChartsService(BaseService):
    """Render the full chart suite from scored items.

    Input: dict with 'scored_items' key.
    """

    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"

    def _get_technologies(self):
        return [ChartsTech()]

    @staticmethod
    def _items_from(data: object) -> list[dict]:
        return items_from(data)

    async def execute_one(self, data: object) -> ServiceResult:
        result = await super().execute_one(data)
        result.input_key = _INPUT_KEY
        return result
