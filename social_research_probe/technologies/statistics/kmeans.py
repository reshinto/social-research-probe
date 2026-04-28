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
    """Fit k-means and return cluster-size results plus within-cluster SS."""
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
    """Return (centroids, assignments) after running Lloyd's algorithm."""
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
    total = 0.0
    for f, a in zip(features, assignments, strict=True):
        total += sum((x - c) ** 2 for x, c in zip(f, centroids[a], strict=True))
    return total
