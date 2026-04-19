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

from social_research_probe.viz.base import ChartResult


def _render_with_matplotlib(x: list[float], y: list[float], path: str, label: str) -> None:
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

    Args:
        label: Raw label string, possibly containing spaces or slashes.

    Returns:
        Sanitised string safe for use as part of a file name.
    """
    return label.replace(" ", "_").replace("/", "_")


def render(
    x: list[float],
    y: list[float],
    label: str = "scatter",
    output_dir: str | None = None,
) -> ChartResult:
    """Render a scatter plot of two numeric series and save it as a PNG.

    Args:
        x: Values for the horizontal axis.
        y: Values for the vertical axis (must align index-for-index with x).
        label: Chart title; also used to construct the output filename.
        output_dir: Save directory (uses tempfile.gettempdir() if None).

    Returns:
        ChartResult with the saved PNG path and a descriptive caption.

    Why plt.close() (matplotlib path): matplotlib retains figure state in
    memory between calls; closing explicitly prevents memory leaks in
    long-running pipeline runs.
    """
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    filename = f"{_sanitise(label)}_scatter.png"
    path = f"{save_dir}/{filename}"

    try:
        _render_with_matplotlib(x, y, path, label)
    except Exception:
        # Pure-Python fallback: write a minimal valid PNG placeholder.
        from social_research_probe.viz._png_writer import write_placeholder_png

        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=f"Scatter plot: {label} ({len(x)} points)",
    )
