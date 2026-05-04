"""Huber-loss robust regression via iteratively reweighted least squares.

Down-weights observations whose residual exceeds k times the MAD so outliers do not
dominate the fit. Returns intercept, slope, and Huber-scaled R² for a
single predictor model ``y ~ x``.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics import StatResult
from social_research_probe.technologies.statistics.multi_regression import _solve_normal_equations


def run(
    x: list[float],
    y: list[float],
    label: str = "y",
    k: float = 1.345,
    max_iter: int = 50,
) -> list[StatResult]:
    """Fit ``y = b0 + b1·x`` using Huber weights and return StatResults.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        x: Numeric series used by the statistical calculation.
        y: Numeric series used by the statistical calculation.
        label: Human-readable metric label included in statistical and chart outputs.
        k: Numeric score, threshold, prior, or confidence value.
        max_iter: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                x=[1.0, 2.0, 3.0],
                y=[1.0, 2.0, 3.0],
                label="engagement",
                k=0.75,
                max_iter=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(x)
    if n < 3 or n != len(y):
        return []
    beta = [0.0, 0.0]
    prev_beta: list[float] = [float("inf"), float("inf")]
    for _ in range(max_iter):
        residuals = [yi - (beta[0] + beta[1] * xi) for xi, yi in zip(x, y, strict=True)]
        scale = _mad(residuals)
        if scale < 1e-12:
            break
        weights = [_huber_weight(r / scale, k) for r in residuals]
        xt_wx = [[0.0, 0.0], [0.0, 0.0]]
        xt_wy = [0.0, 0.0]
        for xi, yi, wi in zip(x, y, weights, strict=True):
            xt_wx[0][0] += wi
            xt_wx[0][1] += wi * xi
            xt_wx[1][0] += wi * xi
            xt_wx[1][1] += wi * xi * xi
            xt_wy[0] += wi * yi
            xt_wy[1] += wi * xi * yi
        new_beta = _solve_normal_equations(xt_wx, xt_wy)
        if new_beta is None:
            return []
        if all(abs(a - b) < 1e-9 for a, b in zip(new_beta, prev_beta, strict=True)):
            beta = new_beta
            break
        prev_beta = beta
        beta = new_beta
    return _build_results(x, y, beta, label)


def _build_results(
    x: list[float], y: list[float], beta: list[float], label: str
) -> list[StatResult]:
    """Build the results structure consumed by the next step.

    Statistics helpers return report-sized records, keeping the calculation and the label shown to
    readers in one place.

    Args:
        x: Numeric series used by the statistical calculation.
        y: Numeric series used by the statistical calculation.
        beta: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _build_results(
                x=[1.0, 2.0, 3.0],
                y=[1.0, 2.0, 3.0],
                beta=[[1.0, 2.0], [3.0, 4.0]],
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    predictions = [beta[0] + beta[1] * xi for xi in x]
    ss_res = sum((yi - pi) ** 2 for yi, pi in zip(y, predictions, strict=True))
    mean_y = sum(y) / len(y)
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return [
        StatResult(
            name=f"huber_intercept_{label}",
            value=beta[0],
            caption=f"Huber intercept for {label}: {beta[0]:.4f}",
        ),
        StatResult(
            name=f"huber_slope_{label}",
            value=beta[1],
            caption=f"Huber slope for {label}: {beta[1]:.6f}",
        ),
        StatResult(
            name=f"huber_r_squared_{label}",
            value=r2,
            caption=f"Huber R² for {label}: {r2:.4f}",
        ),
    ]


def _mad(residuals: list[float]) -> float:
    """Return the mad.

    Args:
        residuals: Residual values from a fitted statistical model.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _mad(
                residuals=["AI safety"],
            )
        Output:
            0.75
    """
    abs_res = sorted(abs(r) for r in residuals)
    n = len(abs_res)
    if n == 0:
        return 0.0
    median = abs_res[n // 2] if n % 2 else (abs_res[n // 2 - 1] + abs_res[n // 2]) / 2
    return median / 0.6745


def _huber_weight(scaled_residual: float, k: float) -> float:
    """Return the huber weight.

    Args:
        scaled_residual: Numeric score, threshold, prior, or confidence value.
        k: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _huber_weight(
                scaled_residual=0.75,
                k=0.75,
            )
        Output:
            0.75
    """
    abs_r = abs(scaled_residual)
    if abs_r <= k:
        return 1.0
    return k / abs_r
