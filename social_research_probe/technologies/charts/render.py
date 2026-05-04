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
    """Document the annotate rule at the boundary where callers use it.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        result: Service or technology result being inspected for payload and diagnostics.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            _annotate(
                result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    annotation = f"_(see PNG: {result.path})_"
    if annotation in result.caption:
        return result
    return replace(result, caption=f"{result.caption}\n{annotation}")


def _scores_field(items: list[dict], field: str) -> list[float]:
    """Compute the scores field used by ranking or analysis.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        field: Metric or data field read from source items.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _scores_field(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                field="AI safety",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [float((d.get("scores") or {}).get(field, 0.0)) for d in items]


def _feature_field(items: list[dict], field: str) -> list[float]:
    """Document the feature field rule at the boundary where callers use it.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        field: Metric or data field read from source items.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _feature_field(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                field="AI safety",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [float((d.get("features") or {}).get(field, 0.0)) for d in items]


def _heatmap_features(items: list[dict]) -> dict[str, list[float]]:
    """Document the heatmap features rule at the boundary where callers use it.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _heatmap_features(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Document the table row rule at the boundary where callers use it.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        rank: Count, database id, index, or limit that bounds the work being performed.
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _table_row(
                rank=3,
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            {"enabled": True}
    """
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
    """Build tabular rows for CSV or HTML output.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _table_rows(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [_table_row(i, d) for i, d in enumerate(items[:10])]


def _ranks_for(items: list[dict]) -> list[float]:
    """Document the ranks for rule at the boundary where callers use it.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _ranks_for(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [float(i) for i in range(len(items))]


def render_bar(items: list[dict], out: Path) -> ChartResult:
    """Create bar output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_bar(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    return _annotate(
        bar.render(_scores_field(items, "overall"), label="overall_score", output_dir=str(out))
    )


def render_line(items: list[dict], out: Path) -> ChartResult:
    """Create line output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_line(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    return _annotate(
        line.render(_scores_field(items, "overall"), label="overall_by_rank", output_dir=str(out))
    )


def render_histogram(items: list[dict], out: Path) -> ChartResult:
    """Create histogram output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_histogram(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    return _annotate(
        histogram.render(
            _scores_field(items, "overall"), label="overall_score", output_dir=str(out)
        )
    )


def render_regression(
    items: list[dict], x_field: str, y_field: str, label: str, out: Path
) -> ChartResult:
    """Create regression output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        x_field: Source-item field used for the chart x-axis.
        y_field: Source-item field used for the chart y-axis.
        label: Human-readable metric label included in statistical and chart outputs.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_regression(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                x_field="AI safety",
                y_field="AI safety",
                label="engagement",
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
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
    """Create scatter output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        x_field: Source-item field used for the chart x-axis.
        y_field: Source-item field used for the chart y-axis.
        label: Human-readable metric label included in statistical and chart outputs.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_scatter(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                x_field="AI safety",
                y_field="AI safety",
                label="engagement",
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    return _annotate(
        scatter.render(
            _scores_field(items, x_field),
            _scores_field(items, y_field),
            label=label,
            output_dir=str(out),
        )
    )


def render_heatmap(items: list[dict], out: Path) -> ChartResult:
    """Create heatmap output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_heatmap(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    return _annotate(
        heatmap.render(_heatmap_features(items), label="feature_correlations", output_dir=str(out))
    )


def render_residuals(items: list[dict], out: Path) -> ChartResult:
    """Create residuals output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_residuals(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    return _annotate(
        residuals.render(
            _ranks_for(items),
            _scores_field(items, "overall"),
            label="overall_by_rank",
            output_dir=str(out),
        )
    )


def render_table(items: list[dict], out: Path) -> ChartResult:
    """Create table output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_table(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    return _annotate(table.render(_table_rows(items), label="top10_summary", output_dir=str(out)))


def _suite_renderers(items: list[dict], out: Path) -> list[Callable[[], ChartResult]]:
    """Document the suite renderers rule at the boundary where callers use it.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            _suite_renderers(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
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
    """Return the safe render.

    Chart helpers normalize inputs before rendering so analysis code does not depend on image-
    generation details.

    Args:
        fn: Renderer or callback function being invoked behind a safe wrapper.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            _safe_render(
                fn=render_chart,
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    try:
        return fn()
    except Exception:
        return None


def render_all(items: list[dict], out: Path) -> list[ChartResult]:
    """Render full chart suite. Skips charts that raise — partial > none.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        out: Output file path where the rendered chart or export artifact should be written.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render_all(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                out="AI safety",
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    if not items:
        return []
    rendered = (_safe_render(fn) for fn in _suite_renderers(items, out))
    return [r for r in rendered if r is not None]
