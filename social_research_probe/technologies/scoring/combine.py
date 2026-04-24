"""Combine trust, trend, and opportunity into one overall score."""

from __future__ import annotations

from collections.abc import Mapping

DEFAULT_WEIGHTS: dict[str, float] = {"trust": 0.45, "trend": 0.30, "opportunity": 0.25}


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def overall_score(
    *,
    trust: float,
    trend: float,
    opportunity: float,
    weights: Mapping[str, float] | None = None,
) -> float:
    """Weighted sum of the three axes, clipped to [0, 1].

    ``weights`` keys (``trust``, ``trend``, ``opportunity``) override the spec §6
    defaults. Missing keys fall back to the default weight for that axis.
    """
    w = DEFAULT_WEIGHTS if weights is None else {**DEFAULT_WEIGHTS, **weights}
    return _clip(w["trust"] * trust + w["trend"] * trend + w["opportunity"] * opportunity)
