"""Chart-type selector for numeric series visualisation.

Chooses the most appropriate chart type based on dataset size and delegates
to the relevant renderer, so callers never need to pick a chart type manually.
"""

from __future__ import annotations

import tempfile

from social_research_probe.technologies.charts.base import ChartResult


def select_and_render(
    data: list[float],
    label: str = "values",
    output_dir: str | None = None,
) -> ChartResult:
    """Choose the appropriate chart type and render it.

    Selection rules:
      - 1 to 5 data points: bar chart (individual values matter most)
      - 6+ data points: line chart (trend over time is more useful)

    Args:
        data: Numeric values to plot.
        label: Chart title and axis label.
        output_dir: Directory to save PNG (uses tempfile.gettempdir() if None).

    Returns:
        A ChartResult with path and caption.

    Why lazy import: avoids circular imports and keeps startup overhead low
    when the selector module is imported but no chart is rendered yet.
    """
    from social_research_probe.technologies.charts import bar, line

    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()

    if len(data) <= 5:
        return bar.render(data, label=label, output_dir=save_dir)
    return line.render(data, label=label, output_dir=save_dir)
