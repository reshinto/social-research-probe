"""Combine trust, trend, and opportunity into one overall score."""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_WEIGHTS: dict[str, float] = {"trust": 0.45, "trend": 0.30, "opportunity": 0.25}


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


def overall_score(
    *,
    trust: float,
    trend: float,
    opportunity: float,
    weights: Mapping[str, float] | None = None,
) -> float:
    """Weighted sum of the three axes, clipped to [0, 1].

    ``weights`` keys (``trust``, ``trend``, ``opportunity``) override the spec §6 defaults. Missing
    keys fall back to the default weight for that axis.

    Args:
        trust: Numeric score, threshold, prior, or confidence value.
        trend: Numeric score, threshold, prior, or confidence value.
        opportunity: Numeric score, threshold, prior, or confidence value.
        weights: Scoring weights used to combine component scores.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            overall_score(
                trust=0.75,
                trend=0.75,
                opportunity=0.75,
                weights="AI safety",
            )
        Output:
            0.75
    """
    w = DEFAULT_WEIGHTS if weights is None else {**DEFAULT_WEIGHTS, **weights}
    return _clip(w["trust"] * trust + w["trend"] * trend + w["opportunity"] * opportunity)
