"""Outlier detection using the z-score method.

Flags values that sit unusually far from the mean, which helps the pipeline
identify viral spikes or data-quality anomalies in a metric series.
"""

from __future__ import annotations

import statistics

from social_research_probe.technologies.statistics.base import StatResult


def run(
    data: list[float],
    label: str = "values",
    threshold: float = 2.0,
) -> list[StatResult]:
    """Identify outliers using the z-score method.

    Args:
        data: Numeric series to analyse.
        label: Human-readable name for this metric, used in captions.
        threshold: Z-score magnitude above which a value is an outlier
                   (default 2.0). Lower values are more aggressive; the
                   conventional social-science threshold is often 3.0.

    Returns:
        List of StatResult objects for 'outlier_count' and 'outlier_fraction',
        or empty list if fewer than 2 data points.

    Why z-score: it normalises deviation by standard deviation, making the
    outlier threshold comparable across metrics with different scales.
    Returns empty list for fewer than 2 data points (z-score needs std dev).
    """
    n = len(data)
    if n < 2:
        return []

    mean_val = statistics.mean(data)
    std_val = statistics.stdev(data)

    if std_val == 0:
        outlier_count = 0
    else:
        outlier_count = sum(1 for v in data if abs((v - mean_val) / std_val) > threshold)

    outlier_fraction = outlier_count / n

    return [
        StatResult(
            name="outlier_count",
            value=float(outlier_count),
            caption=(f"Outliers in {label} (|z| > {threshold}): {outlier_count} of {n}"),
        ),
        StatResult(
            name="outlier_fraction",
            value=outlier_fraction,
            caption=f"Outlier fraction for {label}: {outlier_fraction:.2%}",
        ),
    ]
