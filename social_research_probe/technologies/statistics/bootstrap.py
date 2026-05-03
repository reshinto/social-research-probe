"""Bootstrap confidence intervals for summary statistics.

Classical CIs assume normality. For small samples and skewed
distributions (common in engagement / view-velocity data) the bootstrap
percentile CI is more trustworthy: resample with replacement many times,
compute the statistic on each resample, and read the 2.5-th and 97.5-th
percentiles of the resampling distribution.
"""

from __future__ import annotations

import random
import statistics

from social_research_probe.technologies.statistics import StatResult


def run(
    data: list[float],
    label: str = "values",
    iterations: int = 2000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> list[StatResult]:
    """Return bootstrap distribution summary and percentile CI for the mean.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        label: Human-readable metric label included in statistical and chart outputs.
        iterations: Count, database id, index, or limit that bounds the work being performed.
        ci_level: Numeric score, threshold, prior, or confidence value.
        seed: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                label="engagement",
                iterations=3,
                ci_level=0.75,
                seed=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(data)
    if n < 2:
        return []
    rng = random.Random(seed)
    resamples = _resample_means(data, iterations, rng)
    lower_pct = (1 - ci_level) / 2
    upper_pct = 1 - lower_pct
    lower = _percentile(resamples, lower_pct)
    upper = _percentile(resamples, upper_pct)
    point = statistics.mean(data)
    return [
        StatResult(
            name=f"bootstrap_mean_{label}",
            value=point,
            caption=(
                f"Bootstrap mean of {label}: {point:.4f} "
                f"({int(ci_level * 100)}% CI [{lower:.4f}, {upper:.4f}], "
                f"{iterations} resamples)"
            ),
        ),
        StatResult(
            name=f"bootstrap_ci_lower_{label}",
            value=lower,
            caption=f"Bootstrap CI lower bound for {label}: {lower:.4f}",
        ),
        StatResult(
            name=f"bootstrap_ci_upper_{label}",
            value=upper,
            caption=f"Bootstrap CI upper bound for {label}: {upper:.4f}",
        ),
    ]


def resample_means(data: list[float], iterations: int = 2000, seed: int = 42) -> list[float]:
    """Return the bootstrap distribution of sample means (exposed for viz).

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        iterations: Count, database id, index, or limit that bounds the work being performed.
        seed: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            resample_means(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                iterations=3,
                seed=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return _resample_means(data, iterations, random.Random(seed))


def _resample_means(data: list[float], iterations: int, rng: random.Random) -> list[float]:
    """Document the resample means rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        iterations: Count, database id, index, or limit that bounds the work being performed.
        rng: Random number generator used to keep resampling deterministic in tests.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _resample_means(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                iterations=3,
                rng=random.Random(7),
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    n = len(data)
    return [sum(rng.choice(data) for _ in range(n)) / n for _ in range(iterations)]


def _percentile(sorted_or_unsorted: list[float], p: float) -> float:
    """Return the percentile.

    Args:
        sorted_or_unsorted: Numeric samples that may need ordering before percentile selection.
        p: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _percentile(
                sorted_or_unsorted=["AI safety"],
                p=0.75,
            )
        Output:
            0.75
    """
    ordered = sorted(sorted_or_unsorted)
    if not ordered:
        return 0.0
    k = p * (len(ordered) - 1)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac
