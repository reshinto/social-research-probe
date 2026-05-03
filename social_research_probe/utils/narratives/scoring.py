"""Narrative cluster scoring functions."""

from __future__ import annotations


def compute_confidence(claims: list[dict]) -> float:
    """Mean of claim confidences, clamped to [0.0, 1.0].

    Args:
        claims: List of claim dicts with optional 'confidence' key.

    Returns:
        Float in [0.0, 1.0].
    """
    if not claims:
        return 0.0
    confidences = [float(c.get("confidence") or 0.5) for c in claims]
    raw = sum(confidences) / len(confidences)
    return round(min(max(raw, 0.0), 1.0), 3)


def compute_opportunity_score(claims: list[dict], cluster_type: str) -> float:
    """Score how much this cluster represents an opportunity.

    Higher when cluster_type is opportunity/market_signal, claims are corroborated,
    and sources are diverse.

    Args:
        claims: List of claim dicts.
        cluster_type: The cluster's resolved type.

    Returns:
        Float in [0.0, 1.0].
    """
    if not claims:
        return 0.0
    base = 0.3 if cluster_type in ("opportunity", "market_signal") else 0.0
    n = len(claims)
    supported_ratio = sum(
        1 for c in claims if c.get("corroboration_status") == "supported"
    ) / n
    source_diversity = len({c.get("_source_id", "") for c in claims})
    raw = base + (supported_ratio * 0.4) + min(source_diversity * 0.1, 0.3)
    return round(min(raw, 1.0), 3)


def compute_risk_score(claims: list[dict], cluster_type: str) -> float:
    """Score how much this cluster represents a risk.

    Higher when cluster_type is risk/objection/pain_point, claims are contradicted,
    and claims need review.

    Args:
        claims: List of claim dicts.
        cluster_type: The cluster's resolved type.

    Returns:
        Float in [0.0, 1.0].
    """
    if not claims:
        return 0.0
    base = 0.3 if cluster_type in ("risk", "objection", "pain_point") else 0.0
    n = len(claims)
    contradiction_ratio = sum(
        1 for c in claims if c.get("contradiction_status", "none") != "none"
    ) / n
    review_ratio = sum(1 for c in claims if c.get("needs_review")) / n
    unsupported_ratio = sum(
        1 for c in claims if c.get("corroboration_status") in ("pending", "contradicted")
    ) / n
    raw = base + (contradiction_ratio * 0.3) + (review_ratio * 0.2) + (unsupported_ratio * 0.2)
    return round(min(raw, 1.0), 3)
