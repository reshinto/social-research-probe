"""Growth-rate estimation for ordered numeric series.

Measures average period-over-period percent change so that channels with
very different absolute scales (1 M vs 1 K views) can be compared fairly.
Called by the selector when data has three or more points.
"""

from __future__ import annotations

from social_research_probe.stats.base import StatResult


def run(data: list[float], label: str = "values") -> list[StatResult]:
    """Estimate growth rate from an ordered numeric series.

    Computes the average period-over-period percent change:
    sum((data[i] - data[i-1]) / max(1, abs(data[i-1])) for i in range(1, n)) / (n-1)

    Returns a single StatResult named 'growth_rate'.
    Returns empty list if fewer than 2 data points.

    Args:
        data: Ordered numeric values (e.g. daily view counts, oldest first).
        label: Human-readable name for this metric, used in captions.

    Returns:
        List with a single StatResult for 'growth_rate', or empty list.

    Why period-over-period: absolute differences are not comparable across
    different scales (e.g. a channel with 1M views vs 1K views). Dividing
    by the previous value normalises scale; clamping the denominator to 1
    avoids division-by-zero when a period had zero activity.
    """
    n = len(data)
    if n < 2:
        return []

    # Sum each step's fractional change; clamp denominator to avoid div-by-zero.
    total_change = sum(
        (data[i] - data[i - 1]) / max(1, abs(data[i - 1])) for i in range(1, n)
    )
    growth_rate = total_change / (n - 1)

    return [
        StatResult(
            name="growth_rate",
            value=growth_rate,
            caption=f"Average period-over-period growth rate for {label}: {growth_rate:.2%}",
        )
    ]
