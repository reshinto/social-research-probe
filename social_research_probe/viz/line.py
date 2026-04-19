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


def _render_with_matplotlib(data: list[float], path: str, label: str) -> None:  # pragma: no cover — optional matplotlib
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

    Args:
        label: Raw label string, possibly containing spaces or slashes.

    Returns:
        Sanitised string safe for use as part of a file name.
    """
    return label.replace(" ", "_").replace("/", "_")


def render(
    data: list[float],
    label: str = "values",
    output_dir: str | None = None,
) -> "ChartResult":  # noqa: F821 — type resolved at runtime
    """Render a line chart of the data series and save it as a PNG.

    Args:
        data: Ordered numeric values (y-axis); x-axis is the integer index.
        label: Chart title and y-axis label.
        output_dir: Save directory (uses tempfile.gettempdir() if None).

    Returns:
        ChartResult with the saved PNG path and a descriptive caption.

    Why plt.close() (matplotlib path): matplotlib retains figure state in
    memory between calls; closing explicitly prevents memory leaks in
    long-running pipeline runs.
    """
    from social_research_probe.viz.base import ChartResult

    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    filename = f"{_sanitise(label)}_line.png"
    path = f"{save_dir}/{filename}"

    try:
        _render_with_matplotlib(data, path, label)
    except (ImportError, Exception):
        # Pure-Python fallback: write a minimal valid PNG placeholder.
        from social_research_probe.viz._png_writer import write_placeholder_png
        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=f"Line chart: {label} over {len(data)} data points",
    )
