"""Statistical analysis service."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult
from social_research_probe.utils.display.progress import log_with_time

_NUMERIC_TARGETS: tuple[str, ...] = (
    "overall",
    "trust",
    "trend",
    "opportunity",
    "view_velocity",
    "engagement_ratio",
    "age_days",
    "subscribers",
    "views",
)


class StatisticsService(BaseService):
    """Run statistical analysis on scored research items.

    Input: dict with 'scored_items' key containing list of scored item dicts.
    Builds derived target arrays then runs the stats selector per target.
    """

    service_name: ClassVar[str] = "youtube.analyzing.statistics"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.statistics"

    def _get_technologies(self):
        return []

    @staticmethod
    def _items(data: object) -> list[dict]:
        if not isinstance(data, dict):
            return []
        return [d for d in data.get("scored_items", []) if isinstance(d, dict)]

    @staticmethod
    def _build_targets_dict(items: list[dict]) -> dict[str, list]:
        from social_research_probe.services.analyzing.derived_targets import build_targets
        return build_targets(items)

    @staticmethod
    def _numeric_series(targets: dict[str, list], label: str) -> list[float]:
        return [float(v) for v in targets.get(label, [])]

    @staticmethod
    def _run_for_label(series: list[float], label: str) -> list:
        from social_research_probe.technologies.statistics.selector import select_and_run
        return select_and_run(series, label=label)

    @classmethod
    def _stats_per_target(cls, targets: dict[str, list]) -> dict[str, list]:
        results: dict[str, list] = {}
        for label in _NUMERIC_TARGETS:
            series = cls._numeric_series(targets, label)
            if not series:
                continue
            results[label] = cls._run_for_label(series, label)
        return results

    @staticmethod
    def _highlight_lines(by_target: dict[str, list]) -> list[str]:
        """Each highlight is a StatResult caption like ``"Mean overall: 0.64"``.

        The report renderer infers model + finding from the caption, so do not
        rewrite the separator here.
        """
        return [
            getattr(r, "caption", "")
            for results in by_target.values()
            for r in results
            if getattr(r, "caption", "")
        ]

    @staticmethod
    def _is_low_confidence(items: list[dict]) -> bool:
        return len(items) < 5

    @classmethod
    def _compute(cls, items: list[dict]) -> dict:
        if not items:
            return {"highlights": [], "low_confidence": True}
        by_target = cls._stats_per_target(cls._build_targets_dict(items))
        return {
            "highlights": cls._highlight_lines(by_target),
            "low_confidence": cls._is_low_confidence(items),
        }

    @staticmethod
    def _cache_key(items: list[dict]) -> str:
        from social_research_probe.services.analyzing._dataset_key import dataset_key
        return dataset_key(items, namespace="stats")

    @staticmethod
    def _stats_cache():
        from social_research_probe.utils.caching.pipeline_cache import stage_cache
        return stage_cache("analyze")

    @classmethod
    def _cached_or_compute(cls, items: list[dict]) -> dict:
        from social_research_probe.utils.caching.pipeline_cache import get_json, set_json
        if not items:
            return cls._compute(items)
        cache = cls._stats_cache()
        key = cls._cache_key(items)
        cached = get_json(cache, key)
        if cached is not None:
            return cached
        result = cls._compute(items)
        set_json(cache, key, result)
        return result

    @staticmethod
    async def _compute_async(items: list[dict]) -> dict:
        import asyncio
        return await asyncio.to_thread(StatisticsService._cached_or_compute, items)

    def _success(self, data: object, output: dict) -> TechResult:
        return TechResult(
            tech_name="stats_per_target", input=data, output=output, success=True
        )

    def _failure(self, data: object, exc: Exception) -> TechResult:
        return TechResult(
            tech_name="stats_per_target", input=data, output=None, success=False, error=str(exc)
        )

    async def _run_safely(self, data: object) -> TechResult:
        try:
            output = await self._compute_async(self._items(data))
            return self._success(data, output)
        except Exception as exc:
            return self._failure(data, exc)

    @log_with_time("[srp] {self.service_name}: execute_one")
    async def execute_one(self, data: object) -> ServiceResult:
        """Run stats analysis on scored_items, keyed by derived-target label."""
        tr = await self._run_safely(data)
        return ServiceResult(
            service_name=self.service_name, input_key="scored_items", tech_results=[tr]
        )
