"""K-means clustering via Lloyd's algorithm — pure Python.

Groups items into *k* tiers based on feature similarity. Pure-Python
implementation avoids the numpy/scikit-learn runtime dependency.
"""

from __future__ import annotations

import random

from social_research_probe.technologies.statistics import StatResult


def run(
    features: list[list[float]],
    k: int = 3,
    max_iter: int = 100,
    seed: int = 42,
    label: str = "items",
) -> list[StatResult]:
    """Fit k-means and return cluster-size results plus within-cluster SS.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        k: Count, database id, index, or limit that bounds the work being performed.
        max_iter: Count, database id, index, or limit that bounds the work being performed.
        seed: Count, database id, index, or limit that bounds the work being performed.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                features=[[1.0, 0.2], [2.0, 0.4]],
                k=3,
                max_iter=3,
                seed=3,
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(features)
    if n < k or k < 2:
        return []
    centroids, assignments = fit(features, k=k, max_iter=max_iter, seed=seed)
    if not centroids:
        return []
    wcss = _within_cluster_ss(features, centroids, assignments)
    cluster_sizes = [assignments.count(ci) for ci in range(k)]
    results: list[StatResult] = [
        StatResult(
            name=f"kmeans_k{k}_wcss",
            value=wcss,
            caption=f"K-means (k={k}) within-cluster sum of squares: {wcss:.4f}",
        )
    ]
    for ci, size in enumerate(cluster_sizes):
        results.append(
            StatResult(
                name=f"kmeans_k{k}_cluster_{ci}_size",
                value=float(size),
                caption=f"K-means cluster {ci} contains {size}/{n} {label}",
            )
        )
    return results


def fit(
    features: list[list[float]], k: int = 3, max_iter: int = 100, seed: int = 42
) -> tuple[list[list[float]], list[int]]:
    """Return (centroids, assignments) after running Lloyd's algorithm.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        k: Count, database id, index, or limit that bounds the work being performed.
        max_iter: Count, database id, index, or limit that bounds the work being performed.
        seed: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            fit(
                features=[[1.0, 0.2], [2.0, 0.4]],
                k=3,
                max_iter=3,
                seed=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(features)
    if n < k:
        return [], []
    rng = random.Random(seed)
    centroids = [list(features[i]) for i in rng.sample(range(n), k)]
    assignments: list[int] = [0] * n
    for _ in range(max_iter):
        new_assignments = [_closest(f, centroids) for f in features]
        stable = new_assignments == assignments
        assignments = new_assignments
        if stable:
            return centroids, assignments
        centroids = _recompute_centroids(features, assignments, k, centroids)
    return centroids, assignments


def _closest(point: list[float], centroids: list[list[float]]) -> int:
    """Document the closest rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        point: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        centroids: Numeric vector, matrix, or intermediate value used by the statistical algorithm.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            _closest(
                point=[[1.0, 2.0], [3.0, 4.0]],
                centroids=[[1.0, 2.0], [3.0, 4.0]],
            )
        Output:
            5
    """
    best_idx = 0
    best_dist = float("inf")
    for idx, c in enumerate(centroids):
        d = sum((a - b) ** 2 for a, b in zip(point, c, strict=True))
        if d < best_dist:
            best_dist = d
            best_idx = idx
    return best_idx


def _recompute_centroids(
    features: list[list[float]],
    assignments: list[int],
    k: int,
    prev: list[list[float]],
) -> list[list[float]]:
    """Document the recompute centroids rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        assignments: Numeric vector, matrix, or intermediate value used by the statistical
                     algorithm.
        k: Count, database id, index, or limit that bounds the work being performed.
        prev: Numeric vector, matrix, or intermediate value used by the statistical algorithm.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _recompute_centroids(
                features=[[1.0, 0.2], [2.0, 0.4]],
                assignments=[[1.0, 2.0], [3.0, 4.0]],
                k=3,
                prev=[[1.0, 2.0], [3.0, 4.0]],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    dim = len(features[0])
    new_centroids: list[list[float]] = []
    for ci in range(k):
        members = [f for f, a in zip(features, assignments, strict=True) if a == ci]
        if not members:
            new_centroids.append(list(prev[ci]))
            continue
        new_centroids.append([sum(m[d] for m in members) / len(members) for d in range(dim)])
    return new_centroids


def _within_cluster_ss(
    features: list[list[float]], centroids: list[list[float]], assignments: list[int]
) -> float:
    """Document the within cluster ss rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        centroids: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        assignments: Numeric vector, matrix, or intermediate value used by the statistical
                     algorithm.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _within_cluster_ss(
                features=[[1.0, 0.2], [2.0, 0.4]],
                centroids=[[1.0, 2.0], [3.0, 4.0]],
                assignments=[[1.0, 2.0], [3.0, 4.0]],
            )
        Output:
            0.75
    """
    total = 0.0
    for f, a in zip(features, assignments, strict=True):
        total += sum((x - c) ** 2 for x, c in zip(f, centroids[a], strict=True))
    return total
