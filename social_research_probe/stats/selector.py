"""Analysis selector that chooses which statistical modules to run.

Called by the pipeline to automatically pick an appropriate combination of
analyses based on how much data is available, removing the need for callers
to know the details of each individual module.
"""

from __future__ import annotations

from social_research_probe.stats.base import StatResult


def select_and_run(data: list[float], label: str = "values") -> list[StatResult]:
    """Choose and run appropriate statistical analyses for a numeric series.

    Selection rules (additive — every applicable analysis runs):

    - descriptive: always (for any non-empty series)
    - spread: requires 2+ points (variance / IQR)
    - regression: requires 2+ points (linear fit over index)
    - growth: requires 3+ points (period-over-period change)
    - outliers: requires 3+ points (z-score detection)

    Args:
        data: List of numeric values to analyse (e.g. overall scores).
        label: Human-readable name for this metric, used in captions.

    Returns:
        List of StatResult objects, one per analysis run.

    Why lazy import: avoids circular dependencies since each sub-module also
    imports from this package, and keeps startup cost low.
    """
    from social_research_probe.stats import descriptive, growth, outliers, regression, spread

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
    """Run correlation between two numeric series when both have 2+ points."""
    from social_research_probe.stats import correlation

    if len(series_a) < 2 or len(series_b) < 2:
        return []
    return correlation.run(series_a, series_b, label_a=label_a, label_b=label_b)
