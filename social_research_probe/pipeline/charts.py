"""Chart rendering + data-driven takeaways for the research pipeline output."""

from __future__ import annotations

import statistics
from itertools import combinations
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
    # Distinct from the histogram below by axis (one bar per item vs binned).
    chart = bar_viz.render(overall, label="overall_score_per_item", output_dir=str(charts_dir))
    ascii_chart = chart.caption.split("\n", 1)[1] if "\n" in chart.caption else ""
    title = f"Bar chart: overall score per item, ranked ({len(overall)} items)"
    body = f"{title}\n{ascii_chart}" if ascii_chart else title
    return f"{body}\n_(see PNG: {chart.path})_"


def _render_line(overall: list[float], charts_dir: Path) -> str:
    chart = line_viz.render(overall, label="overall_score_by_rank", output_dir=str(charts_dir))
    ascii_chart = chart.caption.split("\n", 1)[1] if "\n" in chart.caption else ""
    title = f"Line chart: overall score decay across {len(overall)} ranks"
    body = f"{title}\n{ascii_chart}" if ascii_chart else title
    return f"{body}\n_(see PNG: {chart.path})_"


def _render_scatter(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    pretty = label.replace("_", " ").title()
    return f"Scatter (no fit line): {pretty} ({len(x)} items)\n_(see PNG: {chart.path})_"


def _render_histogram(values: list[float], charts_dir: Path) -> str:
    chart = histogram_viz.render(values, label="overall_score", output_dir=str(charts_dir))
    # Raw caption starts with "Histogram: overall_score (...)"; prefix "distribution"
    # to make it clearly distinct from the bar chart above.
    distinctive = chart.caption.replace(
        "Histogram: overall_score", "Histogram: overall score distribution", 1
    )
    return f"{distinctive}\n_(see PNG: {chart.path})_"


def _render_regression(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = regression_scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    pretty = label.replace("_", " ").title()
    distinctive = chart.caption.replace(
        f"Regression: {label}", f"Regression (with fitted line): {pretty}", 1
    )
    return f"{distinctive}\n_(see PNG: {chart.path})_"


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


def _chart_takeaways(scored_items: list[ScoredItem]) -> list[str]:
    """Return deterministic one-line takeaways computed from the scored dataset.

    Zero LLM calls, zero image analysis — derives interpretations from the same
    numbers that feed the charts. Safe to call when charts are disabled.
    """
    if not scored_items:
        return []
    overall = [d["scores"]["overall"] for d in scored_items]
    trust = [d["scores"]["trust"] for d in scored_items]
    trend = [d["scores"]["trend"] for d in scored_items]
    opportunity = [d["scores"]["opportunity"] for d in scored_items]
    takeaways: list[str] = [_interpret_distribution("overall", overall)]
    takeaways.append(_interpret_regression("trust", "opportunity", trust, opportunity))
    takeaways.append(_interpret_regression("trust", "trend", trust, trend))
    takeaways.append(_interpret_strongest_correlation(scored_items))
    outlier = _interpret_outlier(scored_items, overall)
    if outlier:
        takeaways.append(outlier)
    return [t for t in takeaways if t]


def _interpret_distribution(label: str, values: list[float]) -> str:
    """Return a summary sentence for a numeric distribution."""
    if not values:
        return ""
    return (
        f"{label.capitalize()} distribution: n={len(values)}, min={min(values):.2f}, "
        f"median={statistics.median(values):.2f}, max={max(values):.2f}"
    )


def _interpret_regression(x_label: str, y_label: str, xs: list[float], ys: list[float]) -> str:
    """Return slope + r² sentence for a simple linear regression."""
    if len(xs) < 2 or len(ys) < 2:
        return f"{x_label.capitalize()} vs {y_label}: too few points for regression"
    try:
        slope = statistics.linear_regression(xs, ys).slope
        r = statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return f"{x_label.capitalize()} vs {y_label}: undefined (zero variance)"
    strength = _strength_label(abs(r))
    direction = "positive" if slope >= 0 else "negative"
    return (
        f"{x_label.capitalize()} vs {y_label}: slope={slope:+.2f}, r²={r * r:.2f} "
        f"({strength} {direction})"
    )


def _strength_label(abs_r: float) -> str:
    """Map |r| to a qualitative strength label."""
    if abs_r >= 0.7:
        return "strong"
    if abs_r >= 0.4:
        return "moderate"
    if abs_r >= 0.2:
        return "weak"
    return "negligible"


def _interpret_strongest_correlation(scored_items: list[ScoredItem]) -> str:
    """Return the strongest pairwise correlation across the feature matrix."""
    features = _feature_matrix(scored_items)
    best_pair: tuple[str, str] | None = None
    best_r = 0.0
    for (a_name, a_vals), (b_name, b_vals) in combinations(features.items(), 2):
        try:
            r = statistics.correlation(a_vals, b_vals)
        except statistics.StatisticsError:
            continue
        if abs(r) > abs(best_r):
            best_r = r
            best_pair = (a_name, b_name)
    if best_pair is None:
        return "Feature correlations: undefined (zero variance)"
    return f"Feature correlations: strongest pair {best_pair[0]}↔{best_pair[1]} r={best_r:+.2f}"


def _feature_matrix(scored_items: list[ScoredItem]) -> dict[str, list[float]]:
    """Assemble the same numeric feature matrix the heatmap uses."""
    return {
        "trust": [d["scores"]["trust"] for d in scored_items],
        "trend": [d["scores"]["trend"] for d in scored_items],
        "opportunity": [d["scores"]["opportunity"] for d in scored_items],
        "overall": [d["scores"]["overall"] for d in scored_items],
        "velocity": [d["features"]["view_velocity"] for d in scored_items],
        "engagement": [d["features"]["engagement_ratio"] for d in scored_items],
        "age_days": [d["features"]["age_days"] for d in scored_items],
    }


def _interpret_outlier(scored_items: list[ScoredItem], overall: list[float]) -> str | None:
    """Flag the most extreme overall-score outlier when |z| > 2.0."""
    if len(overall) < 3:
        return None
    mean = statistics.fmean(overall)
    stdev = statistics.pstdev(overall)
    if stdev == 0.0:
        return None
    worst_idx, worst_z = 0, 0.0
    for i, value in enumerate(overall):
        z = (value - mean) / stdev
        if abs(z) > abs(worst_z):
            worst_idx, worst_z = i, z
    if abs(worst_z) < 2.0:
        return None
    title = (scored_items[worst_idx].get("title") or "untitled")[:60]
    return f"Outlier detected: {title!r} at z={worst_z:+.1f} on overall score"
