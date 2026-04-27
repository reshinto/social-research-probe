"""Chart rendering technology adapters."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class ChartsTech(BaseTechnology[object, list]):
    """Technology wrapper for generating the full chart suite."""

    name: ClassVar[str] = "charts_suite"

    async def _execute(self, input_data: object) -> list:
        from social_research_probe.services.analyzing.charts import ChartsService

        items = ChartsService._items_from(input_data)
        out_dir = ChartsService._ensure_charts_dir()
        return await ChartsService._render_with_cache(items, out_dir)
