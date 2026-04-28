"""Statistical analysis technology adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology

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


@dataclass
class StatResult:
    """The output of a single statistical analysis."""

    name: str
    value: float
    caption: str


def items_from_data(data: object) -> list[dict]:
    """Extract scored_items list from input data dict."""
    if not isinstance(data, dict):
        return []
    return [d for d in data.get("scored_items", []) if isinstance(d, dict)]


def _build_targets_dict(items: list[dict]) -> dict[str, list]:
    from social_research_probe.utils.analyzing.targets import build_targets

    return build_targets(items)


def _numeric_series(targets: dict[str, list], label: str) -> list[float]:
    return [float(v) for v in targets.get(label, [])]


def _run_for_label(series: list[float], label: str) -> list:
    from social_research_probe.technologies.statistics.selector import select_and_run

    return select_and_run(series, label=label)


def _stats_per_target(targets: dict[str, list]) -> dict[str, list]:
    results: dict[str, list] = {}
    for label in _NUMERIC_TARGETS:
        series = _numeric_series(targets, label)
        if not series:
            continue
        results[label] = _run_for_label(series, label)
    return results


def _highlight_lines(by_target: dict[str, list]) -> list[str]:
    return [
        getattr(r, "caption", "")
        for results in by_target.values()
        for r in results
        if getattr(r, "caption", "")
    ]


def _is_low_confidence(items: list[dict]) -> bool:
    return len(items) < 5


def _compute(items: list[dict]) -> dict:
    if not items:
        return {"highlights": [], "low_confidence": True}
    by_target = _stats_per_target(_build_targets_dict(items))
    return {
        "highlights": _highlight_lines(by_target),
        "low_confidence": _is_low_confidence(items),
    }


def _cache_key(items: list[dict]) -> str:
    from social_research_probe.utils.analyzing.keys import dataset_key

    return dataset_key(items, namespace="stats")


def _stats_cache():
    from social_research_probe.utils.caching.pipeline_cache import stage_cache

    return stage_cache("analyze")


def _cached_or_compute(items: list[dict]) -> dict:
    from social_research_probe.utils.caching.pipeline_cache import get_json, set_json

    if not items:
        return _compute(items)
    cache = _stats_cache()
    key = _cache_key(items)
    cached = get_json(cache, key)
    if cached is not None:
        return cached
    result = _compute(items)
    set_json(cache, key, result)
    return result


async def compute_async(items: list[dict]) -> dict:
    """Run stats computation in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(_cached_or_compute, items)


class StatisticsTech(BaseTechnology[object, dict]):
    """Technology wrapper for computing statistics across all targets."""

    name: ClassVar[str] = "stats_per_target"

    async def _execute(self, input_data: object) -> dict:
        return await compute_async(items_from_data(input_data))
