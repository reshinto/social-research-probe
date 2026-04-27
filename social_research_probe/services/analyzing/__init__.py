"""Analysis services."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from social_research_probe.technologies.charts import (
    bar,
    heatmap,
    histogram,
    line,
    regression_scatter,
    residuals,
    scatter,
    table,
)
from social_research_probe.technologies.charts.base import ChartResult
from social_research_probe.utils.caching.pipeline_cache import hash_key

_ROUND_DIGITS = 6
_VIEW_EVENT_THRESHOLD = 100_000
_TOP_N_CUTOFF = 5


# --- dataset_key ---


def _fingerprint(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "overall_score": round(float(item.get("overall_score", 0.0)), _ROUND_DIGITS),
        "trust": round(float(item.get("trust", 0.0)), _ROUND_DIGITS),
        "trend": round(float(item.get("trend", 0.0)), _ROUND_DIGITS),
        "opportunity": round(float(item.get("opportunity", 0.0)), _ROUND_DIGITS),
    }


def dataset_key(items: list[dict], *, namespace: str) -> str:
    """Return a deterministic cache key for ``items`` under ``namespace``."""
    serialised = json.dumps([_fingerprint(d) for d in items], sort_keys=True)
    return hash_key(namespace, serialised)


# --- charts_suite ---


def _annotate(result: ChartResult) -> ChartResult:
    annotation = f"_(see PNG: {result.path})_"
    if annotation in result.caption:
        return result
    return replace(result, caption=f"{result.caption}\n{annotation}")


def _scores_field(items: list[dict], field: str) -> list[float]:
    return [float(d.get(field, 0.0)) for d in items]


def _feature_field(items: list[dict], field: str) -> list[float]:
    return [float((d.get("features") or {}).get(field, 0.0)) for d in items]


def _heatmap_features(items: list[dict]) -> dict[str, list[float]]:
    return {
        "trust": _scores_field(items, "trust"),
        "trend": _scores_field(items, "trend"),
        "opportunity": _scores_field(items, "opportunity"),
        "overall": _scores_field(items, "overall_score"),
        "velocity": _feature_field(items, "view_velocity"),
        "engagement": _feature_field(items, "engagement_ratio"),
        "age_days": _feature_field(items, "age_days"),
    }


def _table_row(rank: int, item: dict) -> dict:
    return {
        "rank": rank + 1,
        "channel": str(item.get("channel") or item.get("author_name") or "")[:25],
        "trust": f"{float(item.get('trust', 0.0)):.2f}",
        "trend": f"{float(item.get('trend', 0.0)):.2f}",
        "opp": f"{float(item.get('opportunity', 0.0)):.2f}",
        "overall": f"{float(item.get('overall_score', 0.0)):.2f}",
    }


def _table_rows(items: list[dict]) -> list[dict]:
    return [_table_row(i, d) for i, d in enumerate(items[:10])]


def _ranks_for(items: list[dict]) -> list[float]:
    return [float(i) for i in range(len(items))]


def render_bar(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        bar.render(
            _scores_field(items, "overall_score"), label="overall_score", output_dir=str(out)
        )
    )


def render_line(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        line.render(
            _scores_field(items, "overall_score"), label="overall_by_rank", output_dir=str(out)
        )
    )


def render_histogram(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        histogram.render(
            _scores_field(items, "overall_score"), label="overall_score", output_dir=str(out)
        )
    )


def render_regression(
    items: list[dict], x_field: str, y_field: str, label: str, out: Path
) -> ChartResult:
    return _annotate(
        regression_scatter.render(
            _scores_field(items, x_field),
            _scores_field(items, y_field),
            label=label,
            output_dir=str(out),
        )
    )


def render_scatter(
    items: list[dict], x_field: str, y_field: str, label: str, out: Path
) -> ChartResult:
    return _annotate(
        scatter.render(
            _scores_field(items, x_field),
            _scores_field(items, y_field),
            label=label,
            output_dir=str(out),
        )
    )


def render_heatmap(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        heatmap.render(_heatmap_features(items), label="feature_correlations", output_dir=str(out))
    )


def render_residuals(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        residuals.render(
            _ranks_for(items),
            _scores_field(items, "overall_score"),
            label="overall_by_rank",
            output_dir=str(out),
        )
    )


def render_table(items: list[dict], out: Path) -> ChartResult:
    return _annotate(table.render(_table_rows(items), label="top10_summary", output_dir=str(out)))


def _suite_renderers(items: list[dict], out: Path) -> list[Callable[[], ChartResult]]:
    return [
        lambda: render_bar(items, out),
        lambda: render_line(items, out),
        lambda: render_histogram(items, out),
        lambda: render_regression(items, "trust", "opportunity", "trust_vs_opportunity", out),
        lambda: render_regression(items, "trust", "trend", "trust_vs_trend", out),
        lambda: render_scatter(items, "trust", "opportunity", "trust_vs_opportunity", out),
        lambda: render_scatter(items, "trust", "trend", "trust_vs_trend", out),
        lambda: render_heatmap(items, out),
        lambda: render_residuals(items, out),
        lambda: render_table(items, out),
    ]


def _safe_render(fn: Callable[[], ChartResult]) -> ChartResult | None:
    try:
        return fn()
    except Exception:
        return None


def render_all(items: list[dict], out: Path) -> list[ChartResult]:
    """Render full chart suite. Skips charts that raise — partial > none."""
    if not items:
        return []
    rendered = (_safe_render(fn) for fn in _suite_renderers(items, out))
    return [r for r in rendered if r is not None]


# --- derived_targets ---


def _score(items: list[dict], field: str) -> list[float]:
    return [float(d.get(field, 0.0)) for d in items]


def _feature(items: list[dict], field: str) -> list[float]:
    return [float((d.get("features") or {}).get(field, 0.0)) for d in items]


def _ranks(items: list[dict]) -> list[int]:
    return list(range(len(items)))


def _top_tenth_cutoff(n: int) -> int:
    return max(2, n // 10)


def _binary(ranks: list[int], cutoff: int) -> list[int]:
    return [1 if r < cutoff else 0 for r in ranks]


def _views(velocity: list[float], age: list[float]) -> list[float]:
    return [v * a for v, a in zip(velocity, age, strict=True)]


def _event_crossed(views: list[float], threshold: float) -> list[int]:
    return [1 if v >= threshold else 0 for v in views]


def _source_class(items: list[dict]) -> list[str]:
    return [str(d.get("source_class", "unknown")) for d in items]


def build_targets(scored_items: list[dict]) -> dict[str, list]:
    """Return a dict of column-aligned target arrays for downstream models."""
    ranks = _ranks(scored_items)
    velocity = _feature(scored_items, "view_velocity")
    engagement = _feature(scored_items, "engagement_ratio")
    age = _feature(scored_items, "age_days")
    views = _views(velocity, age)
    return {
        "rank": [float(r) for r in ranks],
        "is_top_n": _binary(ranks, _TOP_N_CUTOFF),
        "is_top_tenth": _binary(ranks, _top_tenth_cutoff(len(scored_items))),
        "overall": _score(scored_items, "overall_score"),
        "trust": _score(scored_items, "trust"),
        "trend": _score(scored_items, "trend"),
        "opportunity": _score(scored_items, "opportunity"),
        "view_velocity": velocity,
        "engagement_ratio": engagement,
        "age_days": age,
        "subscribers": _feature(scored_items, "subscriber_count"),
        "views": views,
        "source_class": _source_class(scored_items),
        "event_crossed_100k": _event_crossed(views, _VIEW_EVENT_THRESHOLD),
        "time_to_event_days": age,
    }
