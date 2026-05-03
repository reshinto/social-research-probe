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
    """Return skewness, excess kurtosis, and a plain-English normality verdict.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Return the skew verdict.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        skew: Numeric score, threshold, prior, or confidence value.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _skew_verdict(
                skew=0.75,
            )
        Output:
            "AI safety"
    """
    if abs(skew) < 0.5:
        return "approximately symmetric"
    if skew > 0:
        return "right-skewed — long tail on the right"
    return "left-skewed — long tail on the left"


def _kurt_verdict(kurt: float) -> str:
    """Return the kurt verdict.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        kurt: Numeric score, threshold, prior, or confidence value.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _kurt_verdict(
                kurt=0.75,
            )
        Output:
            "AI safety"
    """
    if abs(kurt) < 1.0:
        return "near-normal tail weight"
    if kurt > 0:
        return "heavy-tailed — more extreme outliers than a normal distribution"
    return "light-tailed — fewer extremes than a normal distribution"


def _classify(skew: float, kurt: float) -> str:
    """Return the classify.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        skew: Numeric score, threshold, prior, or confidence value.
        kurt: Numeric score, threshold, prior, or confidence value.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _classify(
                skew=0.75,
                kurt=0.75,
            )
        Output:
            "AI safety"
    """
    if abs(skew) < 0.5 and abs(kurt) < 1.0:
        return "approximately normal"
    return "non-normal — prefer nonparametric tests"
