"""Claim ledger type definitions."""

from __future__ import annotations

from typing import Literal, TypedDict

ClaimType = Literal[
    "fact_claim",
    "opinion",
    "prediction",
    "recommendation",
    "experience",
    "question",
    "objection",
    "pain_point",
    "market_signal",
]


class ExtractedClaim(TypedDict):
    """One structured claim extracted from an item's primary text.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ExtractedClaim
        Output:
            {"title": "Example"}
    """

    claim_id: str
    source_id: str
    source_url: str
    source_title: str
    claim_text: str
    evidence_text: str
    claim_type: ClaimType
    entities: list[str]
    confidence: float
    evidence_layer: str
    evidence_tier: str
    needs_corroboration: bool
    corroboration_status: str
    contradiction_status: str
    needs_review: bool
    uncertainty: str
    extraction_method: str
    source_sentence: str
    position_in_text: int
    context_before: str
    context_after: str
    extracted_at: str
