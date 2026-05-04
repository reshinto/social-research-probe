"""Descriptive statistics module for numeric series.

Provides mean, median, standard deviation, minimum, and maximum for any
list of floats. Called by the selector when any data is available.
"""

from __future__ import annotations

import statistics

from social_research_probe.technologies.statistics import StatResult


def run(data: list[float], label: str = "values") -> list[StatResult]:
    """Compute basic descriptive statistics for a numeric series.

    Calculates: mean, median, std dev (if >=2 points), min, max.

    Returns an empty list for empty input.

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
    if not data:
        return []

    mean_val = statistics.mean(data)
    median_val = statistics.median(data)
    min_val = min(data)
    max_val = max(data)

    results: list[StatResult] = [
        StatResult(
            name=f"mean_{label}",
            value=mean_val,
            caption=f"Mean {label}: {mean_val:,.4g}",
        ),
        StatResult(
            name=f"median_{label}",
            value=median_val,
            caption=f"Median {label}: {median_val:,.4g}",
        ),
        StatResult(
            name=f"min_{label}",
            value=min_val,
            caption=f"Min {label}: {min_val:,.4g}",
        ),
        StatResult(
            name=f"max_{label}",
            value=max_val,
            caption=f"Max {label}: {max_val:,.4g}",
        ),
    ]

    # Standard deviation requires at least two data points.
    if len(data) >= 2:
        std_val = statistics.stdev(data)
        results.append(
            StatResult(
                name=f"stdev_{label}",
                value=std_val,
                caption=f"Std dev {label}: {std_val:,.4g}",
            )
        )

    return results
