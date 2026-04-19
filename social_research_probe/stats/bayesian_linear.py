"""Conjugate Bayesian linear regression.

Uses a Normal-Inverse-Gamma prior on ``(β, σ²)``. With an uninformative
prior (``κ₀ = 0``, ``a₀ = 0``, ``b₀ = 0``, ``μ₀ = 0``) the posterior mean
equals the OLS solution but the model also reports the posterior
variance of each coefficient, giving Bayesian credible-interval
equivalents without needing MCMC.
"""

from __future__ import annotations

from social_research_probe.stats.base import StatResult
from social_research_probe.stats.multi_regression import _solve_normal_equations


def run(
    y: list[float],
    features: dict[str, list[float]],
    label: str = "y",
    prior_variance: float = 10.0,
) -> list[StatResult]:
    """Fit Bayesian linear regression and return posterior means + std devs."""
    n = len(y)
    names = list(features.keys())
    k = len(names)
    if n == 0 or k == 0 or n <= k + 1:
        return []
    x = [[1.0] + [features[name][i] for name in names] for i in range(n)]
    xt_x = _xtx(x, k + 1)
    prior_precision = 1.0 / prior_variance
    posterior_precision = [
        [xt_x[r][c] + (prior_precision if r == c else 0.0) for c in range(k + 1)]
        for r in range(k + 1)
    ]
    xt_y = [sum(x[i][r] * y[i] for i in range(n)) for r in range(k + 1)]
    beta = _solve_normal_equations(posterior_precision, xt_y)
    if beta is None:
        return []
    residuals = [
        yi - sum(beta[c] * xi[c] for c in range(k + 1)) for xi, yi in zip(x, y, strict=True)
    ]
    ss_res = sum(r * r for r in residuals)
    sigma2 = ss_res / max(n - k - 1, 1)
    posterior_var = _diagonal_of_inverse(posterior_precision, k + 1)
    if posterior_var is None:
        return []
    coef_std = [(sigma2 * v) ** 0.5 for v in posterior_var]
    results: list[StatResult] = [
        StatResult(
            name="bayes_intercept",
            value=beta[0],
            caption=(
                f"Bayesian intercept for {label}: {beta[0]:.4f} (posterior SD {coef_std[0]:.4f})"
            ),
        )
    ]
    for name, coeff, std in zip(names, beta[1:], coef_std[1:], strict=True):
        lower = coeff - 1.96 * std
        upper = coeff + 1.96 * std
        results.append(
            StatResult(
                name=f"bayes_coef_{name}",
                value=coeff,
                caption=(f"Bayesian coef {name}: {coeff:.4f} (95% CrI [{lower:.4f}, {upper:.4f}])"),
            )
        )
    results.append(
        StatResult(
            name="bayes_sigma2",
            value=sigma2,
            caption=f"Bayesian residual variance for {label}: {sigma2:.4f}",
        )
    )
    return results


def _xtx(x: list[list[float]], size: int) -> list[list[float]]:
    n = len(x)
    return [[sum(x[i][r] * x[i][c] for i in range(n)) for c in range(size)] for r in range(size)]


def _diagonal_of_inverse(matrix: list[list[float]], size: int) -> list[float] | None:
    diag: list[float] = []
    for i in range(size):
        e = [1.0 if j == i else 0.0 for j in range(size)]
        column = _solve_normal_equations(matrix, e)
        if column is None:
            return None
        diag.append(column[i])
    return diag
