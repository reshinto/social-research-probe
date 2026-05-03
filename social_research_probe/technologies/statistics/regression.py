"""Simple linear regression (OLS) for ordered numeric series.

Fits a straight line to the data and reports slope and R-squared so callers
can gauge both the direction and the strength of any linear trend. Stdlib only
— no numpy or scipy required.
"""

from __future__ import annotations

import statistics

from social_research_probe.technologies.statistics import StatResult


def run(data: list[float], label: str = "values") -> list[StatResult]:
    """Fit a simple linear regression (ordinary least squares) to the series.

    Returns StatResults for:

    - 'slope': rate of change per unit index step

    - 'r_squared': goodness-of-fit (0=no fit, 1=perfect fit)

    Uses the formula: slope = cov(x,y)/var(x), intercept = mean_y - slope*mean_x.

    Returns empty list for fewer than 2 data points.

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

    # x is the integer index [0, 1, ..., n-1].
    xs = list(range(n))
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(data)

    # Covariance of x and y, and variance of x.
    cov_xy = sum((xs[i] - mean_x) * (data[i] - mean_y) for i in range(n))
    var_x = sum((xs[i] - mean_x) ** 2 for i in range(n))

    slope = cov_xy / var_x
    intercept = mean_y - slope * mean_x

    # R-squared: 1 - SS_res / SS_tot
    ss_res = sum((data[i] - (slope * xs[i] + intercept)) ** 2 for i in range(n))
    ss_tot = sum((data[i] - mean_y) ** 2 for i in range(n))

    # When all y values are identical, ss_tot==0; R-squared is defined as 1.
    r_squared = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot

    return [
        StatResult(
            name="slope",
            value=slope,
            caption=f"Linear trend slope for {label}: {slope:,.4g} per step",
        ),
        StatResult(
            name="r_squared",
            value=r_squared,
            caption=f"R-squared (goodness of fit) for {label}: {r_squared:.4f}",
        ),
    ]
