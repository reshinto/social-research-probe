"""Chart rendering for the research pipeline output."""

from __future__ import annotations

from pathlib import Path

from social_research_probe.types import ScoredItem
from social_research_probe.viz import bar as bar_viz
from social_research_probe.viz import heatmap as heatmap_viz
from social_research_probe.viz import histogram as histogram_viz
from social_research_probe.viz import line as line_viz
from social_research_probe.viz import regression_scatter as regression_scatter_viz
from social_research_probe.viz import residuals as residuals_viz
from social_research_probe.viz import scatter as scatter_viz
from social_research_probe.viz import table as table_viz


def _render_charts(scored_items: list[ScoredItem], data_dir: Path) -> list[str]:
    """Render the full advanced-stats chart suite from the scored dataset.

    Produces: bar, line (rank decay), regression-scatter with fitted line
    (trust vs opp and trust vs trend), plain scatters for backward compat,
    histogram of overall scores, correlation heatmap of all numeric
    features, residuals plot for the rank regression, plus a formatted
    top-10 table.
    """
    if not scored_items:
        return []
    charts_dir = data_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    overall = [d["scores"]["overall"] for d in scored_items]
    trust = [d["scores"]["trust"] for d in scored_items]
    trend = [d["scores"]["trend"] for d in scored_items]
    opportunity = [d["scores"]["opportunity"] for d in scored_items]
    ranks = [float(i) for i in range(len(overall))]

    captions: list[str] = []
    captions.append(_render_bar(overall, charts_dir))
    captions.append(_render_line(overall, charts_dir))
    captions.append(_render_histogram(overall, charts_dir))
    captions.append(_render_regression(trust, opportunity, "trust_vs_opportunity", charts_dir))
    captions.append(_render_regression(trust, trend, "trust_vs_trend", charts_dir))
    captions.append(_render_scatter(trust, opportunity, "trust_vs_opportunity", charts_dir))
    captions.append(_render_scatter(trust, trend, "trust_vs_trend", charts_dir))
    captions.append(_render_heatmap(scored_items, charts_dir))
    captions.append(_render_residuals(ranks, overall, "overall_by_rank", charts_dir))
    captions.append(_render_table(scored_items[:10], charts_dir))
    return captions


def _render_bar(overall: list[float], charts_dir: Path) -> str:
    chart = bar_viz.render(overall, label="overall_score", output_dir=str(charts_dir))
    return chart.caption


def _render_line(overall: list[float], charts_dir: Path) -> str:
    chart = line_viz.render(overall, label="overall_score_by_rank", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_scatter(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"Scatter: {label.replace('_', ' ')} ({len(x)} items)\n_(see PNG: {chart.path})_"


def _render_histogram(values: list[float], charts_dir: Path) -> str:
    chart = histogram_viz.render(values, label="overall_score", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_regression(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = regression_scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_heatmap(scored_items: list[ScoredItem], charts_dir: Path) -> str:
    features = {
        "trust": [d["scores"]["trust"] for d in scored_items],
        "trend": [d["scores"]["trend"] for d in scored_items],
        "opportunity": [d["scores"]["opportunity"] for d in scored_items],
        "overall": [d["scores"]["overall"] for d in scored_items],
        "velocity": [d["features"]["view_velocity"] for d in scored_items],
        "engagement": [d["features"]["engagement_ratio"] for d in scored_items],
        "age_days": [d["features"]["age_days"] for d in scored_items],
    }
    chart = heatmap_viz.render(features, label="feature_correlations", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_residuals(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = residuals_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_table(top5: list[ScoredItem], charts_dir: Path) -> str:
    rows = [
        {
            "rank": i + 1,
            "channel": d["channel"][:25],
            "trust": f"{d['scores']['trust']:.2f}",
            "trend": f"{d['scores']['trend']:.2f}",
            "opp": f"{d['scores']['opportunity']:.2f}",
            "overall": f"{d['scores']['overall']:.2f}",
        }
        for i, d in enumerate(top5)
    ]
    chart = table_viz.render(rows, label="top5_summary", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"
