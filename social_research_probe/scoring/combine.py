def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def overall_score(*, trust: float, trend: float, opportunity: float) -> float:
    return _clip(0.45 * trust + 0.30 * trend + 0.25 * opportunity)
