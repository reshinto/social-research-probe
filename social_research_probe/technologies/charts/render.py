"""Chart suite rendering — pure computation, no service dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from social_research_probe.technologies.charts import (
    ChartResult,
    bar,
    heatmap,
    histogram,
    line,
    regression_scatter,
    residuals,
    scatter,
    table,
)


def _annotate(result: ChartResult) -> ChartResult:
    annotation = f"_(see PNG: {result.path})_"
    if annotation in result.caption:
        return result
    return replace(result, caption=f"{result.caption}\n{annotation}")


def _scores_field(items: list[dict], field: str) -> list[float]:
    return [float((d.get("scores") or {}).get(field, 0.0)) for d in items]


def _feature_field(items: list[dict], field: str) -> list[float]:
    return [float((d.get("features") or {}).get(field, 0.0)) for d in items]


def _heatmap_features(items: list[dict]) -> dict[str, list[float]]:
    return {
        "trust": _scores_field(items, "trust"),
        "trend": _scores_field(items, "trend"),
        "opportunity": _scores_field(items, "opportunity"),
        "overall": _scores_field(items, "overall"),
        "velocity": _feature_field(items, "view_velocity"),
        "engagement": _feature_field(items, "engagement_ratio"),
        "age_days": _feature_field(items, "age_days"),
    }


def _table_row(rank: int, item: dict) -> dict:
    scores = item.get("scores", {})
    return {
        "rank": rank + 1,
        "channel": str(item.get("channel") or item.get("author_name") or "")[:35],
        "trust": f"{float(scores.get('trust', 0.0)):.2f}",
        "trend": f"{float(scores.get('trend', 0.0)):.2f}",
        "opp": f"{float(scores.get('opportunity', 0.0)):.2f}",
        "overall": f"{float(scores.get('overall', 0.0)):.2f}",
    }


def _table_rows(items: list[dict]) -> list[dict]:
    return [_table_row(i, d) for i, d in enumerate(items[:10])]


def _ranks_for(items: list[dict]) -> list[float]:
    return [float(i) for i in range(len(items))]


def render_bar(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        bar.render(_scores_field(items, "overall"), label="overall_score", output_dir=str(out))
    )


def render_line(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        line.render(_scores_field(items, "overall"), label="overall_by_rank", output_dir=str(out))
    )


def render_histogram(items: list[dict], out: Path) -> ChartResult:
    return _annotate(
        histogram.render(
            _scores_field(items, "overall"), label="overall_score", output_dir=str(out)
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
            _scores_field(items, "overall"),
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
