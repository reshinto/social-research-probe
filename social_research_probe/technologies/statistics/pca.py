"""Principal component analysis via power iteration — pure Python.

Extracts the top-``n_components`` principal components of a feature
matrix without numpy. Each component is the eigenvector of the
covariance matrix corresponding to the next-largest eigenvalue, found
via power iteration + deflation.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics import StatResult


def run(
    features: list[list[float]],
    feature_names: list[str],
    n_components: int = 2,
    label: str = "features",
) -> list[StatResult]:
    """Fit PCA and report the variance explained by each of the top components.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        feature_names: Feature matrix, feature names, or target columns used by analysis helpers.
        n_components: Count, database id, index, or limit that bounds the work being performed.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                features=[[1.0, 0.2], [2.0, 0.4]],
                feature_names=["views", "likes"],
                n_components=3,
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Project *features* onto the given principal components.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        components: Numeric vector, matrix, or intermediate value used by the statistical algorithm.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            project(
                features=[[1.0, 0.2], [2.0, 0.4]],
                components=[[1.0, 2.0], [3.0, 4.0]],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    centered, _ = _center(features)
    return [[_dot(row, comp) for comp in components] for row in centered]


def fit_components(features: list[list[float]], n_components: int = 2) -> list[list[float]]:
    """Return just the component vectors (for downstream projection/viz).

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        n_components: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            fit_components(
                features=[[1.0, 0.2], [2.0, 0.4]],
                n_components=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(features)
    if n < 2:
        return []
    centered, _ = _center(features)
    cov = _covariance(centered)
    components, _ = _top_components(cov, n_components)
    return components


def _center(features: list[list[float]]) -> tuple[list[list[float]], list[float]]:
    """Calculate the center step used by the statistical algorithm.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _center(
                features=[[1.0, 0.2], [2.0, 0.4]],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    d = len(features[0])
    means = [sum(row[c] for row in features) / len(features) for c in range(d)]
    centered = [[row[c] - means[c] for c in range(d)] for row in features]
    return centered, means


def _covariance(centered: list[list[float]]) -> list[list[float]]:
    """Calculate the covariance step used by the statistical algorithm.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        centered: Numeric vector, matrix, or intermediate value used by the statistical algorithm.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _covariance(
                centered=[[1.0, 2.0], [3.0, 4.0]],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Calculate the top components step used by the statistical algorithm.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        cov: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        n_components: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _top_components(
                cov=[[1.0, 2.0], [3.0, 4.0]],
                n_components=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Calculate the power iteration step used by the statistical algorithm.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        matrix: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        d: Count, database id, index, or limit that bounds the work being performed.
        iterations: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _power_iteration(
                matrix=[[1.0, 2.0], [3.0, 4.0]],
                d=3,
                iterations=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Calculate the deflate step used by the statistical algorithm.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        matrix: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        vec: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        eig: Numeric score, threshold, prior, or confidence value.
        d: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _deflate(
                matrix=[[1.0, 2.0], [3.0, 4.0]],
                vec=[[1.0, 2.0], [3.0, 4.0]],
                eig=0.75,
                d=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [[matrix[i][j] - eig * vec[i] * vec[j] for j in range(d)] for i in range(d)]


def _format_loadings(component: list[float], feature_names: list[str]) -> str:
    """Format loadings for display or files.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        component: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        feature_names: Feature matrix, feature names, or target columns used by analysis helpers.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _format_loadings(
                component=[[1.0, 2.0], [3.0, 4.0]],
                feature_names=["views", "likes"],
            )
        Output:
            "AI safety"
    """
    pairs = sorted(
        zip(feature_names, component, strict=True),
        key=lambda p: abs(p[1]),
        reverse=True,
    )[:3]
    return ", ".join(f"{name}={value:.2f}" for name, value in pairs)


def _columns(features: list[list[float]]) -> list[list[float]]:
    """Calculate the columns step used by the statistical algorithm.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _columns(
                features=[[1.0, 0.2], [2.0, 0.4]],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    if not features:
        return []
    d = len(features[0])
    return [[row[c] for row in features] for c in range(d)]


def _variance(column: list[float], mean: float) -> float:
    """Return the variance.

    Args:
        column: Numeric column being extracted from a matrix.
        mean: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _variance(
                column=["AI safety"],
                mean=0.75,
            )
        Output:
            0.75
    """
    n = len(column)
    if n < 2:
        return 0.0
    return sum((v - mean) ** 2 for v in column) / (n - 1)


def _dot(row: list[float], comp: list[float]) -> float:
    """Calculate the dot step used by the statistical algorithm.

    Args:
        row: Single source item, database row, or registry entry being transformed.
        comp: Principal component index or vector being formatted.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _dot(
                row={"title": "Example", "url": "https://youtu.be/demo"},
                comp=["AI safety"],
            )
        Output:
            0.75
    """
    return sum(r * c for r, c in zip(row, comp, strict=True))
