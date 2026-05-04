"""Spread (variability) metrics for numeric series.

Reports the interquartile range and simple range so callers can see how
widely the data is dispersed around the centre, complementing the mean and
median provided by the descriptive module.
"""

from __future__ import annotations

import statistics

from social_research_probe.technologies.statistics import StatResult


def run(data: list[float], label: str = "values") -> list[StatResult]:
    """Measure the spread (variability) of a numeric series.

    Returns StatResults for:

    - 'iqr': interquartile range (75th percentile - 25th percentile)

    - 'range': max - min

    Returns empty list for fewer than 4 data points (IQR needs quartiles).

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
    if len(data) < 4:
        return []

    # statistics.quantiles(n=4) returns [Q1, Q2, Q3] (the three cut points).
    q1, _q2, q3 = statistics.quantiles(data, n=4)
    iqr = q3 - q1
    data_range = max(data) - min(data)

    return [
        StatResult(
            name="iqr",
            value=iqr,
            caption=f"Interquartile range of {label}: {iqr:,.4g}",
        ),
        StatResult(
            name="range",
            value=data_range,
            caption=f"Range of {label}: {data_range:,.4g}",
        ),
    ]
