"""Polynomial regression via least-squares normal equations.

Linear regression captures only straight-line trends. When the rank-to-
score curve shows a knee or cliff (as this pipeline often does for the
tail of the distribution), polynomial fits of degree 2 or 3 frequently
report a materially higher R². This module reuses the pure-Python
Gauss-Jordan solver from ``stats.multi_regression`` so no numpy
dependency is required.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics import StatResult
from social_research_probe.technologies.statistics.multi_regression import _solve_normal_equations


def run(x: list[float], y: list[float], label: str = "y", degree: int = 2) -> list[StatResult]:
    """Fit ``y = b0 + b1·x + b2·x² + ... + b_degree·x^degree`` and report R².

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        x: Numeric series used by the statistical calculation.
        y: Numeric series used by the statistical calculation.
        label: Human-readable metric label included in statistical and chart outputs.
        degree: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                x=[1.0, 2.0, 3.0],
                y=[1.0, 2.0, 3.0],
                label="engagement",
                degree=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(x)
    if n <= degree + 1 or degree < 1:
        return []
    x_matrix = [[xi**p for p in range(degree + 1)] for xi in x]
    coeffs = _solve_normal_equations(x_matrix, y)
    if coeffs is None:
        return []
    predictions = [sum(c * row[j] for j, c in enumerate(coeffs)) for row in x_matrix]
    ss_res = sum((yi - pi) ** 2 for yi, pi in zip(y, predictions, strict=True))
    mean_y = sum(y) / n
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    r_squared = 1 - ss_res / ss_tot if ss_tot else 0.0
    return [
        StatResult(
            name=f"poly_deg{degree}_r_squared_{label}",
            value=r_squared,
            caption=f"Polynomial (degree {degree}) R² for {label}: {r_squared:.4f}",
        ),
        StatResult(
            name=f"poly_deg{degree}_coeffs_{label}",
            value=coeffs[-1],
            caption=f"Polynomial (degree {degree}) leading coefficient for {label}: {coeffs[-1]:.6f}",
        ),
    ]


def fit_coefficients(x: list[float], y: list[float], degree: int) -> list[float] | None:
    """Return the raw coefficient vector for use by the viz renderer.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        x: Numeric series used by the statistical calculation.
        y: Numeric series used by the statistical calculation.
        degree: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            fit_coefficients(
                x=[1.0, 2.0, 3.0],
                y=[1.0, 2.0, 3.0],
                degree=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(x)
    if n <= degree + 1 or degree < 1:
        return None
    x_matrix = [[xi**p for p in range(degree + 1)] for xi in x]
    return _solve_normal_equations(x_matrix, y)
