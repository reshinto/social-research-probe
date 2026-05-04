"""Scoring opportunity support.

It keeps provider or algorithm details behind the adapter API used by services.
"""


def _clip(x: float) -> float:
    """Clamp a numeric score into the supported 0-to-1 range.

    Args:
        x: Numeric series used by the statistical calculation.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            _clip(
                x=[1.0, 2.0, 3.0],
            )
        Output:
            0.75
    """
    return max(0.0, min(1.0, x))


def opportunity_score(
    *, market_gap: float, monetization_proxy: float, feasibility: float, novelty: float
) -> float:
    """Compute the opportunity score used by ranking or analysis.

    Args:
        market_gap: Numeric score, threshold, prior, or confidence value.
        monetization_proxy: Numeric score, threshold, prior, or confidence value.
        feasibility: Numeric score, threshold, prior, or confidence value.
        novelty: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            opportunity_score(
                market_gap=0.75,
                monetization_proxy=0.75,
                feasibility=0.75,
                novelty=0.75,
            )
        Output:
            0.75
    """
    return _clip(
        0.40 * market_gap + 0.30 * monetization_proxy + 0.20 * feasibility + 0.10 * novelty
    )
