"""Chart generation service."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult
from social_research_probe.utils.display.progress import log_with_time

_TECH_NAME = "charts_suite"
_INPUT_KEY = "scored_items"


class ChartsService(BaseService):
    """Render the full chart suite from scored items.

    Input: dict with 'scored_items' key.
    Delegates rendering to services/analyzing/charts_suite.render_all.
    """

    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"

    def _get_technologies(self):
        return []

    @staticmethod
    def _data_charts_dir() -> Path:
        from social_research_probe.config import load_active_config

        return load_active_config().data_dir / "charts"

    @classmethod
    def _ensure_charts_dir(cls) -> Path:
        path = cls._data_charts_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _items_from(data: object) -> list[dict]:
        if not isinstance(data, dict):
            return []
        return [d for d in data.get("scored_items", []) if isinstance(d, dict)]

    @staticmethod
    async def _render(items: list[dict], out: Path) -> list:
        import asyncio

        from social_research_probe.services.analyzing.charts_suite import render_all

        return await asyncio.to_thread(render_all, items, out)

    @staticmethod
    def _cache_key(items: list[dict]) -> str:
        from social_research_probe.services.analyzing._dataset_key import dataset_key

        return dataset_key(items, namespace="charts")

    @staticmethod
    def _charts_cache():
        from social_research_probe.utils.caching.pipeline_cache import stage_cache

        return stage_cache("analyze")

    @staticmethod
    def _serialise_results(charts: list, charts_dir: Path) -> dict:
        return {
            "filenames": [Path(c.path).name for c in charts],
            "captions": [c.caption for c in charts],
            "charts_dir": str(charts_dir),
        }

    @staticmethod
    def _restore_results(payload: dict, charts_dir: Path) -> list:
        from social_research_probe.technologies.charts.base import ChartResult

        filenames = payload.get("filenames", [])
        captions = payload.get("captions", [])
        if len(filenames) != len(captions):
            return []
        restored: list = []
        for filename, caption in zip(filenames, captions, strict=True):
            png_path = charts_dir / filename
            if not png_path.exists():
                return []
            restored.append(ChartResult(path=str(png_path), caption=caption))
        return restored

    @classmethod
    async def _render_with_cache(cls, items: list[dict], charts_dir: Path) -> list:
        from social_research_probe.utils.caching.pipeline_cache import get_json, set_json

        if not items:
            return []
        cache = cls._charts_cache()
        key = cls._cache_key(items)
        cached = get_json(cache, key)
        if cached is not None:
            restored = cls._restore_results(cached, charts_dir)
            if restored:
                return restored
        charts = await cls._render(items, charts_dir)
        set_json(cache, key, cls._serialise_results(charts, charts_dir))
        return charts

    @staticmethod
    def _success_result(data: object, charts: list) -> TechResult:
        return TechResult(tech_name=_TECH_NAME, input=data, output=charts, success=True)

    @staticmethod
    def _failure_result(data: object, exc: Exception) -> TechResult:
        return TechResult(
            tech_name=_TECH_NAME, input=data, output=[], success=False, error=str(exc)
        )

    async def _render_safely(self, data: object) -> TechResult:
        try:
            charts = await self._render_with_cache(
                self._items_from(data), self._ensure_charts_dir()
            )
            return self._success_result(data, charts)
        except Exception as exc:
            return self._failure_result(data, exc)

    @log_with_time("[srp] {self.service_name}: execute_one")
    async def execute_one(self, data: object) -> ServiceResult:
        """Render the full chart suite from scored_items in data dict."""
        tr = await self._render_safely(data)
        return ServiceResult(
            service_name=self.service_name, input_key=_INPUT_KEY, tech_results=[tr]
        )
