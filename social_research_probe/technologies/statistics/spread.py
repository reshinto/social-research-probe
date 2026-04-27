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
        data: Numeric series to analyse.
        label: Human-readable name for this metric, used in captions.

    Returns:
        List of StatResult objects for iqr and range, or empty list.

    Why IQR: unlike the full range, IQR is robust to extreme outliers and
    better captures where most of the data actually sits.
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
