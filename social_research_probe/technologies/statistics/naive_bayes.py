"""Gaussian Naive Bayes classifier — pure Python.

Assumes each feature is normally distributed within each class and
features are conditionally independent given the class. Returns prior-
and conditional-density-based StatResults for the majority class plus
training accuracy.
"""

from __future__ import annotations

import math
import statistics

from social_research_probe.technologies.statistics.base import StatResult


def run(
    y: list,
    features: dict[str, list[float]],
    label: str = "y",
) -> list[StatResult]:
    """Fit Gaussian NB and report priors, per-class feature means, and accuracy."""
    n = len(y)
    if n == 0 or len(set(y)) < 2:
        return []
    names = list(features.keys())
    if not names:
        return []
    priors, mus, sigmas = fit(y, features)
    predictions = [predict(row_values(features, i), priors, mus, sigmas) for i in range(n)]
    accuracy = sum(1 for yi, pi in zip(y, predictions, strict=True) if yi == pi) / n
    results: list[StatResult] = []
    for cls, prior in sorted(priors.items()):
        results.append(
            StatResult(
                name=f"nb_prior_{cls}",
                value=prior,
                caption=f"Naive Bayes prior P({label}={cls}): {prior:.4f}",
            )
        )
    results.append(
        StatResult(
            name="nb_accuracy",
            value=accuracy,
            caption=f"Naive Bayes training accuracy for {label}: {accuracy:.4f}",
        )
    )
    return results


def fit(y: list, features: dict[str, list[float]]) -> tuple[dict, dict, dict]:
    """Return (priors, per-class means, per-class stdevs)."""
    classes = sorted(set(y))
    n = len(y)
    priors = {c: sum(1 for yi in y if yi == c) / n for c in classes}
    names = list(features.keys())
    mus: dict = {c: {} for c in classes}
    sigmas: dict = {c: {} for c in classes}
    for c in classes:
        mask = [yi == c for yi in y]
        for name in names:
            values = [v for v, m in zip(features[name], mask, strict=True) if m]
            if len(values) < 2:
                mus[c][name] = statistics.mean(values) if values else 0.0
                sigmas[c][name] = 1.0
            else:
                mus[c][name] = statistics.mean(values)
                sigmas[c][name] = max(statistics.stdev(values), 1e-6)
    return priors, mus, sigmas


def predict(row: dict[str, float], priors: dict, mus: dict, sigmas: dict):
    """Return the class with the highest posterior for *row*."""
    best_cls = None
    best_score = float("-inf")
    for cls, prior in priors.items():
        score = math.log(prior)
        for name, value in row.items():
            mu = mus[cls].get(name, 0.0)
            sigma = sigmas[cls].get(name, 1.0)
            score += -0.5 * math.log(2 * math.pi * sigma * sigma) - ((value - mu) ** 2) / (
                2 * sigma * sigma
            )
        if score > best_score:
            best_score = score
            best_cls = cls
    return best_cls


def row_values(features: dict[str, list[float]], i: int) -> dict[str, float]:
    return {name: features[name][i] for name in features}
