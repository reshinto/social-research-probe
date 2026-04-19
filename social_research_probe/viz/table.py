"""Table renderer that displays row data as a PNG image.

Used to present structured results (e.g. top-performing items) in a
visual format that can be embedded alongside charts. Saves a PNG to disk
and returns the path with a human-readable caption.

Rendering strategy:
  1. Try matplotlib's table widget with the Agg backend.
  2. Fall back to a minimal pure-Python PNG writer when matplotlib's C
     dependencies (numpy) are unavailable for the current Python build.
"""

from __future__ import annotations

import tempfile

from social_research_probe.viz.base import ChartResult


def _render_with_matplotlib(rows: list[dict], path: str, label: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    col_labels = list(rows[0].keys()) if rows else []
    cell_text = [[str(row.get(col, "")) for col in col_labels] for row in rows]

    fig, ax = plt.subplots()
    ax.axis("off")  # Hide axes — only the table should be visible.
    ax.set_title(label)

    if col_labels:
        ax.table(cellText=cell_text, colLabels=col_labels, loc="center")

    plt.savefig(path, bbox_inches="tight")
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
    rows: list[dict],
    label: str = "table",
    output_dir: str | None = None,
) -> ChartResult:
    """Render a simple text table as a PNG using matplotlib's table widget.

    Args:
        rows: List of dicts; keys become column headers. All dicts should
              share the same set of keys for a well-formed table.
        label: Table title; also used to construct the output filename.
        output_dir: Save directory (uses tempfile.gettempdir() if None).

    Returns:
        ChartResult with PNG path and caption.

    Why matplotlib table: keeps the viz package dependency-free (no pandas
    or openpyxl) while still producing a readable tabular image. When
    matplotlib is unavailable the pure-Python PNG fallback produces a
    placeholder file so callers always receive a valid path.
    """
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    filename = f"{_sanitise(label)}_table.png"
    path = f"{save_dir}/{filename}"

    try:
        _render_with_matplotlib(rows, path, label)
    except Exception:
        # Pure-Python fallback: write a minimal valid PNG placeholder.
        from social_research_probe.viz._png_writer import write_placeholder_png

        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=f"Table: {label} ({len(rows)} rows)",
    )
