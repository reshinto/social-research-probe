"""Principal component analysis via power iteration — pure Python.

Extracts the top-``n_components`` principal components of a feature
matrix without numpy. Each component is the eigenvector of the
covariance matrix corresponding to the next-largest eigenvalue, found
via power iteration + deflation.
"""

from __future__ import annotations

from social_research_probe.stats.base import StatResult


def run(
    features: list[list[float]],
    feature_names: list[str],
    n_components: int = 2,
    label: str = "features",
) -> list[StatResult]:
    """Fit PCA and report the variance explained by each of the top components."""
    n = len(features)
    if n < 2 or not features:
        return []
    d = len(features[0])
    if d < 2 or n_components < 1:
        return []
    n_components = min(n_components, d)
    centered, means = _center(features)
    cov = _covariance(centered)
    components, eigenvalues = _top_components(cov, n_components)
    total_var = sum(_variance(col, means[i]) for i, col in enumerate(_columns(features)))
    results: list[StatResult] = []
    for idx, (comp, ev) in enumerate(zip(components, eigenvalues, strict=True)):
        variance_ratio = ev / total_var if total_var else 0.0
        loadings = _format_loadings(comp, feature_names)
        results.append(
            StatResult(
                name=f"pca_pc{idx + 1}_variance_ratio",
                value=variance_ratio,
                caption=(
                    f"PC{idx + 1} for {label} explains {variance_ratio:.1%} of variance "
                    f"(eigenvalue {ev:.4f}); top loadings: {loadings}"
                ),
            )
        )
    return results


def project(features: list[list[float]], components: list[list[float]]) -> list[list[float]]:
    """Project *features* onto the given principal components."""
    centered, _ = _center(features)
    return [[_dot(row, comp) for comp in components] for row in centered]


def fit_components(features: list[list[float]], n_components: int = 2) -> list[list[float]]:
    """Return just the component vectors (for downstream projection/viz)."""
    n = len(features)
    if n < 2:
        return []
    centered, _ = _center(features)
    cov = _covariance(centered)
    components, _ = _top_components(cov, n_components)
    return components


def _center(features: list[list[float]]) -> tuple[list[list[float]], list[float]]:
    d = len(features[0])
    means = [sum(row[c] for row in features) / len(features) for c in range(d)]
    centered = [[row[c] - means[c] for c in range(d)] for row in features]
    return centered, means


def _covariance(centered: list[list[float]]) -> list[list[float]]:
    n = len(centered)
    d = len(centered[0])
    cov = [[0.0] * d for _ in range(d)]
    for row in centered:
        for i in range(d):
            for j in range(d):
                cov[i][j] += row[i] * row[j]
    scale = max(n - 1, 1)
    return [[cov[i][j] / scale for j in range(d)] for i in range(d)]


def _top_components(
    cov: list[list[float]], n_components: int
) -> tuple[list[list[float]], list[float]]:
    d = len(cov)
    matrix = [row[:] for row in cov]
    components: list[list[float]] = []
    eigenvalues: list[float] = []
    for _ in range(n_components):
        vec, eig = _power_iteration(matrix, d)
        components.append(vec)
        eigenvalues.append(eig)
        matrix = _deflate(matrix, vec, eig, d)
    return components, eigenvalues


def _power_iteration(
    matrix: list[list[float]], d: int, iterations: int = 200
) -> tuple[list[float], float]:
    vec = [1.0 / (d**0.5)] * d
    eig = 0.0
    for _ in range(iterations):
        new_vec = [sum(matrix[i][j] * vec[j] for j in range(d)) for i in range(d)]
        norm = sum(v * v for v in new_vec) ** 0.5
        if norm < 1e-12:
            break
        new_vec = [v / norm for v in new_vec]
        eig = sum(new_vec[i] * sum(matrix[i][j] * new_vec[j] for j in range(d)) for i in range(d))
        if all(abs(a - b) < 1e-9 for a, b in zip(new_vec, vec, strict=True)):
            vec = new_vec
            break
        vec = new_vec
    return vec, eig


def _deflate(matrix: list[list[float]], vec: list[float], eig: float, d: int) -> list[list[float]]:
    return [[matrix[i][j] - eig * vec[i] * vec[j] for j in range(d)] for i in range(d)]


def _format_loadings(component: list[float], feature_names: list[str]) -> str:
    pairs = sorted(
        zip(feature_names, component, strict=True),
        key=lambda p: abs(p[1]),
        reverse=True,
    )[:3]
    return ", ".join(f"{name}={value:.2f}" for name, value in pairs)


def _columns(features: list[list[float]]) -> list[list[float]]:
    if not features:
        return []
    d = len(features[0])
    return [[row[c] for row in features] for c in range(d)]


def _variance(column: list[float], mean: float) -> float:
    n = len(column)
    if n < 2:
        return 0.0
    return sum((v - mean) ** 2 for v in column) / (n - 1)


def _dot(row: list[float], comp: list[float]) -> float:
    return sum(r * c for r, c in zip(row, comp, strict=True))
