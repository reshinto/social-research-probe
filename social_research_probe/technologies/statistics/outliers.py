"""Outlier detection using the z-score method.

Flags values that sit unusually far from the mean, which helps the pipeline
identify viral spikes or data-quality anomalies in a metric series.
"""

from __future__ import annotations

import statistics

from social_research_probe.technologies.statistics import StatResult


def run(
    data: list[float],
    label: str = "values",
    threshold: float = 2.0,
) -> list[StatResult]:
    """Identify outliers using the z-score method.

    Statistics helpers return report-sized records, keeping the calculation and the label shown to
    readers in one place.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        label: Human-readable metric label included in statistical and chart outputs.
        threshold: Numeric score, threshold, prior, or confidence value.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            run(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                label="engagement",
                threshold=0.75,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
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
