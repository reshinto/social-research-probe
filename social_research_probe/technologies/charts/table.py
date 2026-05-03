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

from social_research_probe.technologies.charts import ChartResult


def _render_with_matplotlib(rows: list[dict], path: str, label: str) -> None:
    """Create with matplotlib output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        rows: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        path: Filesystem location used to read, write, or resolve project data.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _render_with_matplotlib(
                rows=[[1.0, 2.0], [3.0, 4.0]],
                path=Path("report.html"),
                label="engagement",
            )
        Output:
            None
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    col_labels = list(rows[0].keys()) if rows else []
    cell_text = [[str(row.get(col, "")) for col in col_labels] for row in rows]

    num_cols = max(len(col_labels), 1)
    num_rows = len(cell_text)
    col_width = 3.2
    row_height = 0.7
    fig_width = max(num_cols * col_width, 6)
    fig_height = max((num_rows + 2) * row_height, 3)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    ax.set_title(label, fontsize=14, fontweight="bold", pad=12)

    if col_labels:
        tbl = ax.table(
            cellText=cell_text,
            colLabels=col_labels,
            loc="center",
            cellLoc="center",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(13)
        tbl.scale(1.0, 2.0)

        for (row_idx, _col_idx), cell in tbl.get_celld().items():
            if row_idx == 0:
                cell.set_facecolor("#4472C4")
                cell.set_text_props(color="white", fontweight="bold")
            elif row_idx % 2 == 0:
                cell.set_facecolor("#D9E2F3")

    plt.savefig(path, bbox_inches="tight", dpi=150)
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
    rows: list[dict],
    label: str = "table",
    output_dir: str | None = None,
) -> ChartResult:
    """Render a simple text table as a PNG using matplotlib's table widget.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        rows: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        label: Human-readable metric label included in statistical and chart outputs.
        output_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        ChartResult with the output path and the caption shown in reports.

    Examples:
        Input:
            render(
                rows=[[1.0, 2.0], [3.0, 4.0]],
                label="engagement",
                output_dir=Path(".skill-data"),
            )
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    filename = f"{_sanitise(label)}_table.png"
    path = f"{save_dir}/{filename}"

    try:
        _render_with_matplotlib(rows, path, label)
    except Exception:
        # Pure-Python fallback: write a minimal valid PNG placeholder.
        from social_research_probe.technologies.charts import write_placeholder_png

        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=f"Table: {label} ({len(rows)} rows)",
    )
