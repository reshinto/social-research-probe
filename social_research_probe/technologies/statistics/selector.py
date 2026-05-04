"""Analysis selector that chooses which statistical modules to run.

Called by the pipeline to automatically pick an appropriate combination of
analyses based on how much data is available, removing the need for callers
to know the details of each individual module.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics import StatResult


def select_and_run(data: list[float], label: str = "values") -> list[StatResult]:
    """Choose and run appropriate statistical analyses for a numeric series.

    Selection rules (additive — every applicable analysis runs):

    - descriptive: always (for any non-empty series)

    - spread: requires 2+ points (variance / IQR)

    - regression: requires 2+ points (linear fit over index)

    - growth: requires 3+ points (period-over-period change)

    - outliers: requires 3+ points (z-score detection)

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            select_and_run(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    from social_research_probe.technologies.statistics import (
        descriptive,
        growth,
        outliers,
        regression,
        spread,
    )

    results = descriptive.run(data, label=label)
    if len(data) >= 2:
        results += spread.run(data, label=label)
        results += regression.run(data, label=label)
    if len(data) >= 3:
        results += growth.run(data, label=label)
        results += outliers.run(data, label=label)
    return results


def select_and_run_correlation(
    series_a: list[float],
    series_b: list[float],
    label_a: str = "a",
    label_b: str = "b",
) -> list[StatResult]:
    """Run correlation between two numeric series when both have 2+ points.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        series_a: Numeric series used by the statistical calculation.
        series_b: Numeric series used by the statistical calculation.
        label_a: Human-readable metric label included in statistical and chart outputs.
        label_b: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            select_and_run_correlation(
                series_a=[1.0, 2.0, 3.0],
                series_b=[1.0, 2.0, 3.0],
                label_a="engagement",
                label_b="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    from social_research_probe.technologies.statistics import correlation

    if len(series_a) < 2 or len(series_b) < 2:
        return []
    return correlation.run(series_a, series_b, label_a=label_a, label_b=label_b)
