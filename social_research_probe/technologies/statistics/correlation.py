"""Pearson correlation between two numeric series.

Used to detect whether two social-media signals move together (e.g. views
and engagement), providing a single normalised measure that is scale-invariant.
Stdlib only — no numpy or scipy required.
"""

from __future__ import annotations

import statistics

from social_research_probe.technologies.statistics import StatResult


def run(
    series_a: list[float],
    series_b: list[float],
    label_a: str = "a",
    label_b: str = "b",
) -> list[StatResult]:
    """Compute Pearson correlation coefficient between two series.

    Args:
        series_a: First numeric series.
        series_b: Second numeric series (must be same length as series_a).
        label_a: Human-readable name for the first series.
        label_b: Human-readable name for the second series.

    Returns:
        List with a single StatResult named 'pearson_r', or empty list if
        inputs are too short or differ in length.

    Raises:
        Nothing — all edge cases return an empty list.

    Pearson r = cov(a,b) / (std_a * std_b). A value near +1 or -1 means
    the two signals move together; near 0 means no linear relationship.
    Returns empty list if fewer than 2 points or series are unequal length.
    """
    n = len(series_a)
    if n < 2 or len(series_b) != n:
        return []

    mean_a = statistics.mean(series_a)
    mean_b = statistics.mean(series_b)

    cov = sum((series_a[i] - mean_a) * (series_b[i] - mean_b) for i in range(n))

    var_a = sum((v - mean_a) ** 2 for v in series_a)
    var_b = sum((v - mean_b) ** 2 for v in series_b)
    denom = (var_a * var_b) ** 0.5

    if denom == 0:
        return []

    pearson_r = cov / denom

    return [
        StatResult(
            name="pearson_r",
            value=pearson_r,
            caption=(
                f"Pearson r between {label_a} and {label_b}: {pearson_r:.4f} "
                f"({'positive' if pearson_r >= 0 else 'negative'} correlation)"
            ),
        )
    ]
