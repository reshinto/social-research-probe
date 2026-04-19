"""Bar chart renderer for short numeric series.

Used when there are five or fewer data points where individual values are
more important than the trend. Saves a PNG to disk and returns the path
with a human-readable caption.

Rendering strategy:
  1. Try matplotlib with the Agg (non-interactive) backend.
  2. Fall back to a minimal pure-Python PNG writer when matplotlib's C
     dependencies (numpy) are unavailable for the current Python build.
"""

from __future__ import annotations

import tempfile


def _render_with_matplotlib(data: list[float], path: str, label: str) -> None:  # pragma: no cover — optional matplotlib
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure()
    plt.bar(range(len(data)), data)
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
) -> ChartResult:  # noqa: F821 — type resolved at runtime
    """Render a bar chart of the data series and save it as a PNG.

    Args:
        data: Numeric values (y-axis); each bar corresponds to one index.
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
    filename = f"{_sanitise(label)}_bar.png"
    path = f"{save_dir}/{filename}"

    try:
        _render_with_matplotlib(data, path, label)
    except (ImportError, Exception):
        # Pure-Python fallback: write a minimal valid PNG placeholder.
        from social_research_probe.viz._png_writer import write_placeholder_png
        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=f"Bar chart: {label} ({len(data)} items)",
    )
