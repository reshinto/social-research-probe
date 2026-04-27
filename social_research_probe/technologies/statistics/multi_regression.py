"""Multiple linear regression via normal equations.

Fits y = b0 + b1·x1 + b2·x2 + ... using the closed-form OLS solution
``β = (XᵀX)⁻¹ Xᵀy``. Emits per-coefficient StatResults plus model-level
R² and adjusted R², so consumers can see which features drive the
dependent variable and how well the combined model explains it.

The implementation uses only the Python stdlib — no numpy. This keeps
the module deployable in the same constrained runtimes (e.g. free-
threaded CPython) where numpy's C extensions fail to load.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics.base import StatResult


def run(
    y: list[float],
    features: dict[str, list[float]],
    label: str = "y",
) -> list[StatResult]:
    """Fit a multi-feature OLS model and return coefficients plus fit metrics.

    Args:
        y: Dependent variable values (same length as each feature column).
        features: Mapping of feature-name to column values. Adds an
            implicit intercept; callers should not pass one.
        label: Name of the dependent variable, used in captions.

    Returns:
        List of StatResults — one per coefficient (plus intercept), plus
        ``r_squared`` and ``adjusted_r_squared``. Returns an empty list
        when the sample size is too small for the feature count.
    """
    n = len(y)
    feature_names = list(features.keys())
    k = len(feature_names)
    if n == 0 or k == 0 or n <= k + 1:
        return []

    x_matrix = [[1.0] + [features[name][i] for name in feature_names] for i in range(n)]
    coeffs = _solve_normal_equations(x_matrix, y)
    if coeffs is None:
        return []

    predictions = [sum(c * row[j] for j, c in enumerate(coeffs)) for row in x_matrix]
    residuals = [yi - pi for yi, pi in zip(y, predictions, strict=True)]
    ss_res = sum(r * r for r in residuals)
    mean_y = sum(y) / n
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    r_squared = 1 - ss_res / ss_tot if ss_tot else 0.0
    adjusted = 1 - (1 - r_squared) * (n - 1) / (n - k - 1) if n > k + 1 else r_squared

    results: list[StatResult] = [
        StatResult(
            name="intercept",
            value=coeffs[0],
            caption=f"Intercept for {label}: {coeffs[0]:.4f}",
        )
    ]
    for name, coeff in zip(feature_names, coeffs[1:], strict=True):
        results.append(
            StatResult(
                name=f"coef_{name}",
                value=coeff,
                caption=f"Coefficient for {name}: {coeff:.4f}",
            )
        )
    results.append(
        StatResult(
            name="multi_r_squared",
            value=r_squared,
            caption=f"Multi-regression R² for {label}: {r_squared:.4f}",
        )
    )
    results.append(
        StatResult(
            name="adjusted_r_squared",
            value=adjusted,
            caption=f"Adjusted R² for {label}: {adjusted:.4f}",
        )
    )
    return results


def _solve_normal_equations(x_matrix: list[list[float]], y: list[float]) -> list[float] | None:
    """Solve β = (XᵀX)⁻¹ Xᵀy via Gauss-Jordan elimination. None on singularity."""
    n = len(x_matrix)
    cols = len(x_matrix[0])
    xt_x = [
        [sum(x_matrix[k][i] * x_matrix[k][j] for k in range(n)) for j in range(cols)]
        for i in range(cols)
    ]
    xt_y = [sum(x_matrix[k][i] * y[k] for k in range(n)) for i in range(cols)]
    return _gauss_jordan_solve(xt_x, xt_y)


def _gauss_jordan_solve(matrix: list[list[float]], rhs: list[float]) -> list[float] | None:
    """Solve ``matrix · x = rhs`` in place. Returns None if matrix is singular."""
    size = len(matrix)
    augmented = [[*row, rhs[i]] for i, row in enumerate(matrix)]
    for i in range(size):
        pivot = _pivot_index(augmented, i, size)
        if pivot is None:
            return None
        if pivot != i:
            augmented[i], augmented[pivot] = augmented[pivot], augmented[i]
        _eliminate_column(augmented, i, size)
    return [row[-1] for row in augmented]


def _pivot_index(augmented: list[list[float]], col: int, size: int) -> int | None:
    """Return the row index with the largest absolute pivot value, or None."""
    best_row = col
    best_abs = abs(augmented[col][col])
    for r in range(col + 1, size):
        if abs(augmented[r][col]) > best_abs:
            best_row = r
            best_abs = abs(augmented[r][col])
    return best_row if best_abs > 1e-12 else None


def _eliminate_column(augmented: list[list[float]], col: int, size: int) -> None:
    """Divide the pivot row then eliminate *col* from all other rows in place."""
    pivot_value = augmented[col][col]
    augmented[col] = [value / pivot_value for value in augmented[col]]
    for r in range(size):
        if r == col:
            continue
        factor = augmented[r][col]
        augmented[r] = [
            augmented[r][c] - factor * augmented[col][c] for c in range(len(augmented[col]))
        ]
