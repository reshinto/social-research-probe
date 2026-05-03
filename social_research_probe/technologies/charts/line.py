"""Line chart renderer for ordered numeric series.

Used when there are six or more data points and a trend over time is more
informative than a bar chart. Saves a PNG to disk and returns the path with
a human-readable caption.

Rendering strategy:
  1. Try matplotlib with the Agg (non-interactive) backend.
  2. If matplotlib is unavailable (e.g. its numpy C extension is broken for
     the current Python build), fall back to a minimal pure-Python PNG writer
     that produces a valid placeholder file so callers still get a real path.
"""

from __future__ import annotations

import tempfile

from social_research_probe.technologies.charts import ChartResult
from social_research_probe.technologies.charts.ascii import render_bars as render_ascii_bars


def _render_with_matplotlib(data: list[float], path: str, label: str) -> None:
    """Create with matplotlib output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        path: Filesystem location used to read, write, or resolve project data.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _render_with_matplotlib(
                data={"title": "Example", "url": "https://youtu.be/demo"},
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
    plt.plot(data)
    plt.title(label)
    plt.ylabel(label)
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
    data: list[float],
    label: str = "values",
    output_dir: str | None = None,
) -> ChartResult:
    """Render a line chart of the data series and save it as a PNG.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        label: Human-readable metric label included in statistical and chart outputs.
        output_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                label="engagement",
                output_dir=Path(".skill-data"),
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    filename = f"{_sanitise(label)}_line.png"
    path = f"{save_dir}/{filename}"

    try:
        _render_with_matplotlib(data, path, label)
    except Exception:
        # Pure-Python fallback: write a minimal valid PNG placeholder.
        from social_research_probe.technologies.charts import write_placeholder_png

        write_placeholder_png(path)

    ascii_chart = render_ascii_bars(data, label=label)
    return ChartResult(
        path=path,
        caption=f"Line chart: {label} over {len(data)} data points\n{ascii_chart}",
    )
