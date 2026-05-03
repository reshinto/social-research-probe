"""Residuals-vs-fitted plot for a simple linear regression.

Diagnostic chart: after fitting y ~ slope·x + intercept, plot residuals
(actual minus predicted) against fitted values. Random scatter around
zero means the linear model captures the pattern; a curve or funnel shape
means the model is missing non-linearity or has heteroskedasticity.
"""

from __future__ import annotations

import tempfile

from social_research_probe.technologies.charts import ChartResult


def _fit_and_residuals(x: list[float], y: list[float]) -> tuple[list[float], list[float]]:
    """Document the fit and residuals rule at the boundary where callers use it.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        x: Numeric series used by the statistical calculation.
        y: Numeric series used by the statistical calculation.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _fit_and_residuals(
                x=[1.0, 2.0, 3.0],
                y=[1.0, 2.0, 3.0],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(x)
    if n < 2:
        return [], []
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y, strict=True))
    den = sum((xi - mean_x) ** 2 for xi in x)
    slope = num / den if den else 0.0
    intercept = mean_y - slope * mean_x
    fitted = [slope * xi + intercept for xi in x]
    residuals = [yi - fi for yi, fi in zip(y, fitted, strict=True)]
    return fitted, residuals


def _render_with_matplotlib(
    fitted: list[float], residuals: list[float], path: str, label: str
) -> None:
    """Create with matplotlib output for users or downstream tools.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        fitted: Fitted model values aligned with the original observations.
        residuals: Residual values from a fitted statistical model.
        path: Filesystem location used to read, write, or resolve project data.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _render_with_matplotlib(
                fitted=["AI safety"],
                residuals=["AI safety"],
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
    plt.scatter(fitted, residuals, alpha=0.7)
    plt.axhline(0.0, color="red", linestyle="--", linewidth=2)
    plt.title(f"Residuals vs fitted: {label}")
    plt.xlabel("fitted value")
    plt.ylabel("residual (actual minus predicted)")
    plt.savefig(path)
    plt.close(fig)


def _sanitise(label: str) -> str:
    """Sanitize a label so it is safe to use in generated filenames.

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
    x: list[float], y: list[float], label: str = "residuals", output_dir: str | None = None
) -> ChartResult:
    """Document the render rule at the boundary where callers use it.

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
    path = f"{save_dir}/{_sanitise(label)}_residuals.png"
    fitted, residuals = _fit_and_residuals(x, y)

    if fitted:
        try:
            _render_with_matplotlib(fitted, residuals, path, label)
        except Exception:
            from social_research_probe.technologies.charts import write_placeholder_png

            write_placeholder_png(path)
    else:
        from social_research_probe.technologies.charts import write_placeholder_png

        write_placeholder_png(path)

    max_abs = max((abs(r) for r in residuals), default=0.0)
    return ChartResult(
        path=path,
        caption=(
            f"Residuals vs fitted: {label} ({len(fitted)} points, max|residual|={max_abs:.4f})"
        ),
    )
