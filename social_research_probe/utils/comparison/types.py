"""Comparison data model type definitions."""

from __future__ import annotations

from typing import Literal, TypedDict

ChangeStatus = Literal["new", "repeated", "disappeared"]


class SourceChange(TypedDict):
    """Delta record for one source between two runs."""

    source_id: int
    platform: str
    external_id: str
    url: str
    title: str
    status: ChangeStatus
    score_changes: dict[str, float]
    evidence_tier_baseline: str
    evidence_tier_target: str


class ClaimChange(TypedDict):
    """Delta record for one claim between two runs."""

    claim_id: str
    claim_text: str
    claim_type: str
    source_url: str
    status: ChangeStatus
    confidence_change: float
    corroboration_changed: bool
    baseline_corroboration: str
    target_corroboration: str
    review_status_changed: bool


class NarrativeChange(TypedDict):
    """Delta record for one narrative between two runs."""

    narrative_id: str
    title: str
    cluster_type: str
    status: ChangeStatus
    match_method: str
    matched_id: str
    confidence_change: float
    opportunity_change: float
    risk_change: float
    claim_count_change: int
    source_count_change: int
    strength_signal: str


class TrendSignal(TypedDict):
    """One detected trend signal from comparison."""

    signal_type: str
    title: str
    description: str
    narrative_id: str
    score: float


class RunInfo(TypedDict):
    """Metadata about one run in a comparison."""

    run_pk: int
    run_id: str
    topic: str
    platform: str
    started_at: str
    finished_at: str
    source_count: int
    claim_count: int
    narrative_count: int


class ComparisonResult(TypedDict):
    """Full result of comparing two runs."""

    baseline: RunInfo
    target: RunInfo
    source_changes: list[SourceChange]
    claim_changes: list[ClaimChange]
    narrative_changes: list[NarrativeChange]
    trends: list[TrendSignal]
    counts: dict[str, int]
    follow_ups: list[str]
