"""Scatter plot with an overlaid least-squares regression line and R² label.

A plain scatter shows the cloud of points; a regression scatter adds the
line of best fit and the coefficient of determination (R²) so the viewer
can see both the relationship and how strong it is at a glance.
"""

from __future__ import annotations

import tempfile

from social_research_probe.technologies.charts import ChartResult


def _fit_line(x: list[float], y: list[float]) -> tuple[float, float, float]:
    """Return (slope, intercept, r_squared) from a simple OLS fit."""
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y, strict=True))
    den_x = sum((xi - mean_x) ** 2 for xi in x)
    den_y = sum((yi - mean_y) ** 2 for yi in y)
    slope = num / den_x if den_x else 0.0
    intercept = mean_y - slope * mean_x
    r_squared = (num * num / (den_x * den_y)) if (den_x and den_y) else 0.0
    return slope, intercept, r_squared


def _render_with_matplotlib(
    x: list[float],
    y: list[float],
    path: str,
    label: str,
    slope: float,
    intercept: float,
    r_squared: float,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure()
    plt.scatter(x, y, alpha=0.7)
    if x:
        x_line = [min(x), max(x)]
        y_line = [slope * xv + intercept for xv in x_line]
        plt.plot(
            x_line, y_line, color="red", linewidth=2, label=f"y = {slope:.3f}x + {intercept:.3f}"
        )
    plt.title(f"{label}  (R²={r_squared:.3f})")
    if x:
        plt.legend(loc="best")
    plt.savefig(path)
    plt.close(fig)


def _sanitise(label: str) -> str:
    return label.replace(" ", "_").replace("/", "_")


def render(
    x: list[float],
    y: list[float],
    label: str = "regression",
    output_dir: str | None = None,
) -> ChartResult:
    """Render a regression scatter and return path plus stat-rich caption."""
    slope, intercept, r_squared = _fit_line(x, y) if len(x) >= 2 else (0.0, 0.0, 0.0)
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    path = f"{save_dir}/{_sanitise(label)}_regression.png"

    try:
        _render_with_matplotlib(x, y, path, label, slope, intercept, r_squared)
    except Exception:
        from social_research_probe.technologies.charts import write_placeholder_png

        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=(
            f"Regression: {label} ({len(x)} points, slope={slope:.4f}, "
            f"intercept={intercept:.4f}, R²={r_squared:.3f})"
        ),
    )
