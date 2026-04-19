"""Analysis selector that chooses which statistical modules to run.

Called by the pipeline to automatically pick an appropriate combination of
analyses based on how much data is available, removing the need for callers
to know the details of each individual module.
"""

from __future__ import annotations

from social_research_probe.stats.base import StatResult


def select_and_run(data: list[float], label: str = "values") -> list[StatResult]:
    """Choose and run appropriate statistical analyses for a numeric series.

    Runs descriptive stats always. Adds growth analysis when data has >=3 points.

    Args:
        data: List of numeric values to analyse (e.g. view counts).
        label: Human-readable name for this metric, used in captions.

    Returns:
        List of StatResult objects, one per analysis run.

    Why lazy import: avoids circular dependencies since each sub-module also
    imports from this package, and keeps startup cost low.
    """
    from social_research_probe.stats import descriptive, growth

    results = descriptive.run(data, label=label)
    if len(data) >= 3:
        results += growth.run(data, label=label)
    return results
