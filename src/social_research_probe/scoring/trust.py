def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))

def trust_score(*, source_class: float, channel_credibility: float,
                citation_traceability: float, ai_slop_penalty: float,
                corroboration_score: float) -> float:
    return _clip(
        0.35 * source_class
        + 0.25 * channel_credibility
        + 0.15 * citation_traceability
        + 0.15 * (1.0 - ai_slop_penalty)
        + 0.10 * corroboration_score
    )
