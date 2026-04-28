"""Analysis services."""

from __future__ import annotations

# Re-exports kept for backwards compatibility.
from social_research_probe.technologies.charts.render import (
    _annotate,
    _safe_render,
    render_all,
    render_bar,
    render_heatmap,
    render_histogram,
    render_line,
    render_regression,
    render_residuals,
    render_scatter,
    render_table,
)
from social_research_probe.utils.analyzing.keys import dataset_key
from social_research_probe.utils.analyzing.targets import build_targets

__all__ = [
    "_annotate",
    "_safe_render",
    "render_all",
    "render_bar",
    "render_heatmap",
    "render_histogram",
    "render_line",
    "render_regression",
    "render_residuals",
    "render_scatter",
    "render_table",
    "dataset_key",
    "build_targets",
]
