"""Gaussian Naive Bayes classifier — pure Python.

Assumes each feature is normally distributed within each class and
features are conditionally independent given the class. Returns prior-
and conditional-density-based StatResults for the majority class plus
training accuracy.
"""

from __future__ import annotations

import math
import statistics

from social_research_probe.technologies.statistics import StatResult


def run(
    y: list,
    features: dict[str, list[float]],
    label: str = "y",
) -> list[StatResult]:
    """Fit Gaussian NB and report priors, per-class feature means, and accuracy.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        y: Numeric series used by the statistical calculation.
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                y=[1.0, 2.0, 3.0],
                features=[[1.0, 0.2], [2.0, 0.4]],
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Return (priors, per-class means, per-class stdevs).

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        y: Numeric series used by the statistical calculation.
        features: Feature matrix, feature names, or target columns used by analysis helpers.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            fit(
                y=[1.0, 2.0, 3.0],
                features=[[1.0, 0.2], [2.0, 0.4]],
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
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
    """Document the predict rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        row: Single source item, database row, or registry entry being transformed.
        priors: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        mus: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        sigmas: Numeric vector, matrix, or intermediate value used by the statistical algorithm.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            predict(
                row={"title": "Example", "url": "https://youtu.be/demo"},
                priors=[[1.0, 2.0], [3.0, 4.0]],
                mus=[[1.0, 2.0], [3.0, 4.0]],
                sigmas=[[1.0, 2.0], [3.0, 4.0]],
            )
        Output:
            "AI safety"
    """
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
    """Document the row values rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        features: Feature matrix, feature names, or target columns used by analysis helpers.
        i: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            row_values(
                features=[[1.0, 0.2], [2.0, 0.4]],
                i=3,
            )
        Output:
            {"enabled": True}
    """
    return {name: features[name][i] for name in features}
