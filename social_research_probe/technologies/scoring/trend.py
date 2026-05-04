"""Scoring trend support.

It keeps provider or algorithm details behind the adapter API used by services.
"""

import math


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


def recency_decay(age_days: float) -> float:
    """Document the recency decay rule at the boundary where callers use it.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        age_days: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            recency_decay(
                age_days=0.75,
            )
        Output:
            0.75
    """
    return math.exp(-max(0.0, age_days) / 30.0)


def trend_score(
    *,
    z_view_velocity: float,
    z_engagement_ratio: float,
    z_cross_channel_repetition: float,
    age_days: float,
) -> float:
    """Compute the trend score used by ranking or analysis.

    Args:
        z_view_velocity: Numeric score, threshold, prior, or confidence value.
        z_engagement_ratio: Numeric score, threshold, prior, or confidence value.
        z_cross_channel_repetition: Numeric score, threshold, prior, or confidence value.
        age_days: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            trend_score(
                z_view_velocity=0.75,
                z_engagement_ratio=0.75,
                z_cross_channel_repetition=0.75,
                age_days=0.75,
            )
        Output:
            0.75
    """

    def norm_z(z: float) -> float:
        """Document the norm z rule at the boundary where callers use it.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            z: Numeric score, threshold, prior, or confidence value.

        Returns:
            Numeric score, threshold, or measurement used by analysis and reporting code.

        Examples:
            Input:
                norm_z(
                    z=0.75,
                )
            Output:
                0.75
        """
        return _clip(0.5 + z / 6.0)

    return _clip(
        0.40 * norm_z(z_view_velocity)
        + 0.20 * norm_z(z_engagement_ratio)
        + 0.20 * norm_z(z_cross_channel_repetition)
        + 0.20 * recency_decay(age_days)
    )
