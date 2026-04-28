"""Chart generation service."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult
from social_research_probe.technologies.charts import (
    ChartsTech,
    _restore_results,
    _serialise_results,
    items_from,
)
from social_research_probe.technologies.charts import (
    _cache_key as _cache_key_fn,
)
from social_research_probe.technologies.charts import (
    _charts_cache as _charts_cache_fn,
)

_INPUT_KEY = "scored_items"


class ChartsService(BaseService):
    """Render the full chart suite from scored items.

    Input: dict with 'scored_items' key.
    Delegates rendering to technologies/charts render_with_cache.
    """

    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"

    def _get_technologies(self):
        return [ChartsTech()]

    @staticmethod
    def _items_from(data: object) -> list[dict]:
        return items_from(data)

    @staticmethod
    def _charts_cache():
        return _charts_cache_fn()

    @staticmethod
    def _serialise_results(charts: list, charts_dir: Path) -> dict:
        return _serialise_results(charts, charts_dir)

    @staticmethod
    def _restore_results(payload: dict, charts_dir: Path) -> list:
        return _restore_results(payload, charts_dir)

    @staticmethod
    async def _render(items: list[dict], out: Path) -> list:
        import asyncio

        import social_research_probe.technologies.charts.render as _render_mod

        return await asyncio.to_thread(_render_mod.render_all, items, out)

    @classmethod
    async def _render_with_cache(cls, items: list[dict], charts_dir: Path) -> list:
        from social_research_probe.utils.caching.pipeline_cache import get_json, set_json

        if not items:
            return []
        cache = cls._charts_cache()
        key = _cache_key_fn(items)
        cached = get_json(cache, key)
        if cached is not None:
            restored = cls._restore_results(cached, charts_dir)
            if restored:
                return restored
        charts = await cls._render(items, charts_dir)
        set_json(cache, key, cls._serialise_results(charts, charts_dir))
        return charts

    async def execute_one(self, data: object) -> ServiceResult:
        result = await super().execute_one(data)
        result.input_key = _INPUT_KEY
        return result
