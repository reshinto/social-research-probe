import math


def _clip(x: float) -> float: return max(0.0, min(1.0, x))

def recency_decay(age_days: float) -> float:
    return math.exp(-max(0.0, age_days) / 30.0)

def trend_score(*, z_view_velocity: float, z_engagement_ratio: float,
                z_cross_channel_repetition: float, age_days: float) -> float:
    def norm_z(z: float) -> float: return _clip(0.5 + z / 6.0)
    return _clip(
        0.40 * norm_z(z_view_velocity)
        + 0.20 * norm_z(z_engagement_ratio)
        + 0.20 * norm_z(z_cross_channel_repetition)
        + 0.20 * recency_decay(age_days)
    )
