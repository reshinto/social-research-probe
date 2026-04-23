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

from social_research_probe.technologies.statistics.base import StatResult


def run(
    data: list[float],
    label: str = "values",
    iterations: int = 2000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> list[StatResult]:
    """Return bootstrap distribution summary and percentile CI for the mean."""
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
    """Return the bootstrap distribution of sample means (exposed for viz)."""
    return _resample_means(data, iterations, random.Random(seed))


def _resample_means(data: list[float], iterations: int, rng: random.Random) -> list[float]:
    n = len(data)
    return [sum(rng.choice(data) for _ in range(n)) / n for _ in range(iterations)]


def _percentile(sorted_or_unsorted: list[float], p: float) -> float:
    ordered = sorted(sorted_or_unsorted)
    if not ordered:
        return 0.0
    k = p * (len(ordered) - 1)
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    frac = k - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac
