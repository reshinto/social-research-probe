"""Binary logistic regression via iteratively reweighted least squares (IRLS).

log-likelihood. Pure Python — uses the Gauss-Jordan solver from

``multi_regression``. Reports each coefficient, the McFadden pseudo-R²,
and accuracy on the training set.
"""

from __future__ import annotations

import math

from social_research_probe.technologies.statistics import StatResult
from social_research_probe.technologies.statistics.multi_regression import _solve_normal_equations


def run(
    y: list[int], features: dict[str, list[float]], label: str = "y", max_iter: int = 25
) -> list[StatResult]:
    """Fit binary logistic regression and return coefficients plus fit metrics.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        y: Numeric series used by the statistical calculation.
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        label: Human-readable metric label included in statistical and chart outputs.
        max_iter: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                y=[1.0, 2.0, 3.0],
                features=[[1.0, 0.2], [2.0, 0.4]],
                label="engagement",
                max_iter=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(y)
    if n == 0:
        return []
    names = list(features.keys())
    k = len(names)
    if k == 0:
        return []
    if n <= k + 1:
        return []
    if not (0 < sum(y) < n):
        return []
    x = [[1.0] + [features[name][i] for name in names] for i in range(n)]
    beta = [0.0] * (k + 1)
    for _ in range(max_iter):
        p = [_sigmoid(_dot(row, beta)) for row in x]
        w = [pi * (1 - pi) for pi in p]
        if all(wi < 1e-10 for wi in w):
            break
        z = [
            _dot(row, beta) + (yi - pi) / (wi if wi > 1e-10 else 1e-10)
            for row, yi, pi, wi in zip(x, y, p, w, strict=True)
        ]
        xt_wx = [
            [sum(x[i][r] * w[i] * x[i][c] for i in range(n)) for c in range(k + 1)]
            for r in range(k + 1)
        ]
        xt_wz = [sum(x[i][r] * w[i] * z[i] for i in range(n)) for r in range(k + 1)]
        new_beta = _solve_normal_equations(xt_wx, xt_wz)
        if new_beta is None:
            return []
        if all(abs(a - b) < 1e-8 for a, b in zip(new_beta, beta, strict=True)):
            beta = new_beta
            break
        beta = new_beta
    return _format_results(y, x, beta, names, label)


def _format_results(
    y: list[int], x: list[list[float]], beta: list[float], names: list[str], label: str
) -> list[StatResult]:
    """Format results for display or files.

    Statistics helpers return report-sized records, keeping the calculation and the label shown to
    readers in one place.

    Args:
        y: Numeric series used by the statistical calculation.
        x: Numeric series used by the statistical calculation.
        beta: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        names: Topic, purpose, or provider names being matched against stored state.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _format_results(
                y=[1.0, 2.0, 3.0],
                x=[1.0, 2.0, 3.0],
                beta=[[1.0, 2.0], [3.0, 4.0]],
                names=["AI safety"],
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    predictions = [_sigmoid(_dot(row, beta)) for row in x]
    preds_bin = [1 if p >= 0.5 else 0 for p in predictions]
    accuracy = sum(1 for yi, pi in zip(y, preds_bin, strict=True) if yi == pi) / len(y)
    ll_model = sum(_safe_log(p if yi else 1 - p) for yi, p in zip(y, predictions, strict=True))
    mean_y = sum(y) / len(y)
    ll_null = sum(yi * _safe_log(mean_y) + (1 - yi) * _safe_log(1 - mean_y) for yi in y)
    pseudo_r2 = 1 - ll_model / ll_null if ll_null else 0.0
    results: list[StatResult] = [
        StatResult(
            name="logistic_intercept",
            value=beta[0],
            caption=f"Logistic intercept for {label}: {beta[0]:.4f}",
        )
    ]
    for name, coeff in zip(names, beta[1:], strict=True):
        if coeff > 500:
            or_str = "odds ratio > 1e217"
        elif coeff < -500:
            or_str = "odds ratio < 1e-217"
        else:
            or_str = f"odds ratio {math.exp(coeff):.3f}"
        results.append(
            StatResult(
                name=f"logistic_coef_{name}",
                value=coeff,
                caption=f"Logistic coefficient for {name}: {coeff:.4f} ({or_str})",
            )
        )
    results.append(
        StatResult(
            name="logistic_pseudo_r_squared",
            value=pseudo_r2,
            caption=f"McFadden pseudo-R² for {label}: {pseudo_r2:.4f}",
        )
    )
    results.append(
        StatResult(
            name="logistic_accuracy",
            value=accuracy,
            caption=f"Training accuracy for {label}: {accuracy:.4f}",
        )
    )
    return results


def _sigmoid(z: float) -> float:
    """Return the sigmoid.

    Args:
        z: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _sigmoid(
                z=0.75,
            )
        Output:
            0.75
    """
    if z < -500:
        return 0.0
    if z > 500:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def _dot(row: list[float], beta: list[float]) -> float:
    """Calculate the dot step used by the statistical algorithm.

    Args:
        row: Single source item, database row, or registry entry being transformed.
        beta: Numeric vector, matrix, or intermediate value used by the statistical algorithm.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _dot(
                row={"title": "Example", "url": "https://youtu.be/demo"},
                beta=[[1.0, 2.0], [3.0, 4.0]],
            )
        Output:
            0.75
    """
    return sum(r * b for r, b in zip(row, beta, strict=True))


def _safe_log(p: float) -> float:
    """Document the safe log rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        p: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _safe_log(
                p=0.75,
            )
        Output:
            0.75
    """
    return math.log(max(1e-12, min(1.0 - 1e-12, p)))
