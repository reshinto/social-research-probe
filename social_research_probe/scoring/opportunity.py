def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def opportunity_score(
    *, market_gap: float, monetization_proxy: float, feasibility: float, novelty: float
) -> float:
    return _clip(
        0.40 * market_gap + 0.30 * monetization_proxy + 0.20 * feasibility + 0.10 * novelty
    )
