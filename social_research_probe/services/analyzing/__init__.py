"""Analysis services."""

from __future__ import annotations

# Re-exports kept for backwards compatibility.
from social_research_probe.technologies.charts.render import (  # noqa: F401
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
from social_research_probe.utils.analyzing.keys import dataset_key  # noqa: F401
from social_research_probe.utils.analyzing.targets import build_targets  # noqa: F401
