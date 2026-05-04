"""Growth-rate estimation for ordered numeric series.

Measures average period-over-period percent change so that channels with
very different absolute scales (1 M vs 1 K views) can be compared fairly.
Called by the selector when data has three or more points.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics import StatResult


def run(data: list[float], label: str = "values") -> list[StatResult]:
    """Estimate growth rate from an ordered numeric series.

    Computes the average period-over-period percent change:

    sum((data[i] - data[i-1]) / max(1, abs(data[i-1])) for i in range(1, n)) / (n-1)

    Returns a single StatResult named 'growth_rate'.

    Returns empty list if fewer than 2 data points.

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
    n = len(data)
    if n < 2:
        return []

    # Sum each step's fractional change; clamp denominator to avoid div-by-zero.
    total_change = sum((data[i] - data[i - 1]) / max(1, abs(data[i - 1])) for i in range(1, n))
    growth_rate = total_change / (n - 1)

    return [
        StatResult(
            name="growth_rate",
            value=growth_rate,
            caption=f"Average period-over-period growth rate for {label}: {growth_rate:.2%}",
        )
    ]
