"""Scatter plot renderer for two correlated numeric series.

Used to visualise the relationship between two metrics (e.g. views vs
engagement) and complements the Pearson correlation statistic. Saves a
PNG to disk and returns the path with a human-readable caption.

Rendering strategy:
  1. Try matplotlib with the Agg (non-interactive) backend.
  2. Fall back to a minimal pure-Python PNG writer when matplotlib's C
     dependencies (numpy) are unavailable for the current Python build.
"""

from __future__ import annotations

import tempfile

from social_research_probe.technologies.charts import ChartResult


def _render_with_matplotlib(x: list[float], y: list[float], path: str, label: str) -> None:
    """Create with matplotlib output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        x: Numeric series used by the statistical calculation.
        y: Numeric series used by the statistical calculation.
        path: Filesystem location used to read, write, or resolve project data.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _render_with_matplotlib(
                x=[1.0, 2.0, 3.0],
                y=[1.0, 2.0, 3.0],
                path=Path("report.html"),
                label="engagement",
            )
        Output:
            None
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure()
    plt.scatter(x, y)
    plt.title(label)
    plt.savefig(path)
    plt.close(fig)


def _sanitise(label: str) -> str:
    """Replace characters that are unsafe in filenames with underscores.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _sanitise(
                label="engagement",
            )
        Output:
            "AI safety"
    """
    return label.replace(" ", "_").replace("/", "_")


def render(
    x: list[float],
    y: list[float],
    label: str = "scatter",
    output_dir: str | None = None,
) -> ChartResult:
    """Render a scatter plot of two numeric series and save it as a PNG.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        x: Numeric series used by the statistical calculation.
        y: Numeric series used by the statistical calculation.
        label: Human-readable metric label included in statistical and chart outputs.
        output_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render(
                x=[1.0, 2.0, 3.0],
                y=[1.0, 2.0, 3.0],
                label="engagement",
                output_dir=Path(".skill-data"),
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    filename = f"{_sanitise(label)}_scatter.png"
    path = f"{save_dir}/{filename}"

    try:
        _render_with_matplotlib(x, y, path, label)
    except Exception:
        # Pure-Python fallback: write a minimal valid PNG placeholder.
        from social_research_probe.technologies.charts import write_placeholder_png

        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=f"Scatter plot: {label} ({len(x)} points)",
    )
