"""Chart-type selector for numeric series visualisation.

Chooses the most appropriate chart type based on dataset size and delegates
to the relevant renderer, so callers never need to pick a chart type manually.
"""

from __future__ import annotations

import tempfile

from social_research_probe.technologies.charts import ChartResult


def select_and_render(
    data: list[float],
    label: str = "values",
    output_dir: str | None = None,
) -> ChartResult:
    """Choose the appropriate chart type and render it.

    Selection rules: - 1 to 5 data points: bar chart (individual values matter most)

    - 6+ data points: line chart (trend over time is more useful)

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        label: Human-readable metric label included in statistical and chart outputs.
        output_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            select_and_render(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                label="engagement",
                output_dir=Path(".skill-data"),
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    from social_research_probe.technologies.charts import bar, line

    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()

    if len(data) <= 5:
        return bar.render(data, label=label, output_dir=save_dir)
    return line.render(data, label=label, output_dir=save_dir)
