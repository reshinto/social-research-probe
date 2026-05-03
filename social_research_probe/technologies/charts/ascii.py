"""Pure-text bar/line chart renderer for terminal-first consumers.

PNG charts saved by ``viz.bar`` and ``viz.line`` are only useful when the
caller opens the file in an image viewer. CLI and skill consumers see the
output stream directly, so they need an inline visualisation that does not
require leaving the terminal. This module returns a small Unicode bar chart
that can be embedded in the chart caption alongside the saved PNG path.
"""

from __future__ import annotations

_BAR_CHAR = "█"
_DEFAULT_WIDTH = 30


def render_bars(data: list[float], label: str = "values", width: int = _DEFAULT_WIDTH) -> str:
    """Return a multi-line Unicode bar chart for *data*.

    Bars are scaled so the largest value fills *width* columns. Values are printed to three
    decimal places — enough resolution for normalised scores in the 0-to-1 range without
    overwhelming the line.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        label: Human-readable metric label included in statistical and chart outputs.
        width: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            render_bars(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                label="engagement",
                width=3,
            )
        Output:
            "AI safety"
    """
    if not data:
        return f"{label}: (no data)"
    scale = max(data) or 1.0
    rows = [f"{label} ({len(data)} items)"]
    for index, value in enumerate(data, start=1):
        bar = _BAR_CHAR * max(1, int((value / scale) * width))
        rows.append(f"  #{index}  {value:.3f}  {bar}")
    return "\n".join(rows)
