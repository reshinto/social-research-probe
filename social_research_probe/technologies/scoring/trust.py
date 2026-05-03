"""Scoring trust support.

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


def trust_score(
    *,
    source_class: float,
    channel_credibility: float,
    citation_traceability: float,
    ai_slop_penalty: float,
    corroboration_score: float,
) -> float:
    """Compute the trust score used by ranking or analysis.

    Args:
        source_class: Source-class label such as primary, secondary, commentary, or unknown.
        channel_credibility: Numeric score, threshold, prior, or confidence value.
        citation_traceability: Numeric score, threshold, prior, or confidence value.
        ai_slop_penalty: Numeric score, threshold, prior, or confidence value.
        corroboration_score: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            trust_score(
                source_class="primary",
                channel_credibility=0.75,
                citation_traceability=0.75,
                ai_slop_penalty=0.75,
                corroboration_score=0.75,
            )
        Output:
            0.75
    """
    return _clip(
        0.35 * source_class
        + 0.25 * channel_credibility
        + 0.15 * citation_traceability
        + 0.15 * (1.0 - ai_slop_penalty)
        + 0.10 * corroboration_score
    )
