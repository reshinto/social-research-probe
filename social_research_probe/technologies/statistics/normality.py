"""Normality diagnostics via sample skewness and excess kurtosis.

Classical hypothesis tests (t-test, ANOVA, Pearson correlation) assume
residuals are approximately normal. This module reports shape statistics
and a simple rule-of-thumb verdict so the reader knows whether the
parametric machinery applies or whether they should lean on the
nonparametric results instead.
"""

from __future__ import annotations

import statistics

from social_research_probe.technologies.statistics import StatResult


def run(data: list[float], label: str = "values") -> list[StatResult]:
    """Return skewness, excess kurtosis, and a plain-English normality verdict."""
    n = len(data)
    if n < 4:
        return []
    mean_val = statistics.mean(data)
    variance = statistics.pvariance(data)
    if variance == 0:
        return []
    std = variance**0.5
    skew = sum(((x - mean_val) / std) ** 3 for x in data) / n
    kurt = sum(((x - mean_val) / std) ** 4 for x in data) / n - 3.0
    verdict = _classify(skew, kurt)
    return [
        StatResult(
            name=f"skewness_{label}",
            value=skew,
            caption=f"Skewness of {label}: {skew:.4f} ({_skew_verdict(skew)})",
        ),
        StatResult(
            name=f"excess_kurtosis_{label}",
            value=kurt,
            caption=f"Excess kurtosis of {label}: {kurt:.4f} ({_kurt_verdict(kurt)})",
        ),
        StatResult(
            name=f"normality_verdict_{label}",
            value=0.0 if verdict == "approximately normal" else 1.0,
            caption=f"Normality check for {label}: {verdict}",
        ),
    ]


def _skew_verdict(skew: float) -> str:
    if abs(skew) < 0.5:
        return "approximately symmetric"
    if skew > 0:
        return "right-skewed — long tail on the right"
    return "left-skewed — long tail on the left"


def _kurt_verdict(kurt: float) -> str:
    if abs(kurt) < 1.0:
        return "near-normal tail weight"
    if kurt > 0:
        return "heavy-tailed — more extreme outliers than a normal distribution"
    return "light-tailed — fewer extremes than a normal distribution"


def _classify(skew: float, kurt: float) -> str:
    if abs(skew) < 0.5 and abs(kurt) < 1.0:
        return "approximately normal"
    return "non-normal — prefer nonparametric tests"
