"""Compute composite quality score for extracted claims."""

from __future__ import annotations

_TIER_SCORES: dict[str, float] = {
    "metadata_transcript": 1.0,
    "metadata_comments": 0.7,
    "metadata_only": 0.4,
}

_CORROBORATION_SCORES: dict[str, float] = {
    "supported": 1.0,
    "pending": 0.5,
    "refuted": 0.0,
}

_METHOD_SCORES: dict[str, float] = {
    "llm": 0.9,
    "deterministic": 0.6,
}

_WEIGHTS: dict[str, float] = {
    "confidence": 0.30,
    "evidence_tier": 0.25,
    "corroboration": 0.20,
    "method": 0.15,
    "grounding": 0.10,
}


def compute_quality_score(claim: dict) -> float:
    """0.0-1.0 composite from 5 weighted factors.

    Args:
        claim: Claim text or claim dictionary being extracted, classified, reviewed, or
               corroborated.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            compute_quality_score(
                claim={"text": "The model reduces latency by 30%."},
            )
        Output:
            0.75
    """
    raw_conf = claim.get("confidence")
    if isinstance(raw_conf, (int, float)) and not isinstance(raw_conf, bool):
        confidence = max(0.0, min(1.0, float(raw_conf)))
    else:
        confidence = 0.5

    tier = _TIER_SCORES.get(claim.get("evidence_tier", ""), 0.5)
    corroboration = _CORROBORATION_SCORES.get(claim.get("corroboration_status", ""), 0.5)
    method = _METHOD_SCORES.get(claim.get("extraction_method", ""), 0.5)

    pos = claim.get("position_in_text")
    grounding = 1.0 if isinstance(pos, int) and pos > 0 else 0.5

    score = (
        _WEIGHTS["confidence"] * confidence
        + _WEIGHTS["evidence_tier"] * tier
        + _WEIGHTS["corroboration"] * corroboration
        + _WEIGHTS["method"] * method
        + _WEIGHTS["grounding"] * grounding
    )
    return max(0.0, min(1.0, score))
