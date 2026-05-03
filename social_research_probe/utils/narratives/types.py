"""Narrative clustering type definitions."""

from __future__ import annotations

from typing import Literal, TypedDict

ClusterType = Literal[
    "theme",
    "objection",
    "pain_point",
    "opportunity",
    "risk",
    "market_signal",
    "question",
    "prediction",
    "mixed",
]

CLUSTER_TYPE_VALUES: frozenset[str] = frozenset(
    {
        "theme",
        "objection",
        "pain_point",
        "opportunity",
        "risk",
        "market_signal",
        "question",
        "prediction",
        "mixed",
    }
)


class NarrativeCluster(TypedDict):
    """One narrative cluster grouping related claims across sources."""

    narrative_id: str
    title: str
    summary: str
    cluster_type: ClusterType
    claim_ids: list[str]
    source_ids: list[str]
    source_urls: list[str]
    representative_claims: list[str]
    entities: list[str]
    keywords: list[str]
    evidence_tiers: list[str]
    corroboration_statuses: list[str]
    source_count: int
    claim_count: int
    confidence: float
    opportunity_score: float
    risk_score: float
    contradiction_count: int
    needs_review_count: int
    created_at: str
