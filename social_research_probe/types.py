"""Shared typed dicts and aliases used across configuration, state, and packets.

This module exists to keep the codebase on one vocabulary for the major nested
payloads that move between config loading, state storage, pipeline processing,
and rendering. The goal is not perfect static modelling of every dynamic field;
the goal is to remove vague untyped annotations and replace them with stable,
reviewable shapes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, NotRequired, TypeAlias, TypedDict

JSONScalar: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]

MetricValue: TypeAlias = None | bool | int | float | str
MetricMap: TypeAlias = dict[str, MetricValue]

RunnerName = Literal["none", "claude", "gemini", "codex", "local"]
FreeTextRunnerName = Literal["claude", "gemini", "codex", "local"]


class RunnerSettings(TypedDict, total=False):
    """Per-runner CLI settings loaded from config.toml."""

    binary: str
    model: str
    extra_flags: list[str]


class LLMConfigSection(TypedDict):
    """Top-level [llm] config section with per-runner nested settings."""

    runner: RunnerName
    timeout_seconds: int
    claude: RunnerSettings
    gemini: RunnerSettings
    codex: RunnerSettings
    local: RunnerSettings


class CorroborationConfigSection(TypedDict):
    """Top-level corroboration settings."""

    backend: str
    max_claims_per_item: int
    max_claims_per_session: int


class YouTubePlatformConfig(TypedDict, total=False):
    """Configurable defaults for the YouTube adapter."""

    recency_days: int
    max_items: int
    cache_ttl_search_hours: int
    cache_ttl_channel_hours: int


class PlatformsConfigSection(TypedDict):
    """Current platform defaults keyed by platform name."""

    youtube: YouTubePlatformConfig


class ScoringConfigSection(TypedDict):
    """Scoring config section with optional weight overrides."""

    weights: dict[str, float]


class AppConfig(TypedDict):
    """Canonical in-memory shape of config.toml after defaults are applied."""

    llm: LLMConfigSection
    corroboration: CorroborationConfigSection
    platforms: PlatformsConfigSection
    scoring: ScoringConfigSection


class AdapterConfig(TypedDict, total=False):
    """Runtime adapter config assembled from file defaults plus CLI overrides."""

    data_dir: Path
    include_shorts: bool
    fetch_transcripts: bool
    recency_days: int
    max_items: int
    cache_ttl_search_hours: int
    cache_ttl_channel_hours: int


class PurposeEntry(TypedDict):
    """One persisted purpose entry from purposes.json."""

    method: str
    evidence_priorities: list[str]
    scoring_overrides: NotRequired[dict[str, float]]


class TopicsState(TypedDict):
    """Persisted topics.json structure."""

    schema_version: int
    topics: list[str]


class PurposesState(TypedDict):
    """Persisted purposes.json structure."""

    schema_version: int
    purposes: dict[str, PurposeEntry]


DuplicateStatusValue = Literal["new", "near-duplicate", "duplicate"]


class PendingTopicSuggestion(TypedDict):
    """One staged topic suggestion."""

    id: int
    value: str
    reason: str
    duplicate_status: DuplicateStatusValue
    matches: list[str]


class PendingPurposeSuggestion(TypedDict):
    """One staged purpose suggestion."""

    id: int
    name: str
    method: str
    evidence_priorities: list[str]
    duplicate_status: DuplicateStatusValue
    matches: list[str]


class PendingSuggestionsState(TypedDict):
    """Persisted pending_suggestions.json structure."""

    schema_version: int
    pending_topic_suggestions: list[PendingTopicSuggestion]
    pending_purpose_suggestions: list[PendingPurposeSuggestion]


class TopicSuggestionCandidate(TypedDict, total=False):
    """Unpersisted topic suggestion candidate before staging."""

    value: str
    reason: str


class PurposeSuggestionCandidate(TypedDict, total=False):
    """Unpersisted purpose suggestion candidate before staging."""

    name: str
    method: str
    evidence_priorities: list[str]


class ScoreBreakdown(TypedDict):
    """Per-item score breakdown used by the packet renderer."""

    trust: float
    trend: float
    opportunity: float
    overall: float


class ItemFeatures(TypedDict):
    """Derived numeric features that downstream stats and charts consume."""

    view_velocity: float
    engagement_ratio: float
    age_days: float
    subscriber_count: float


class ScoredItem(TypedDict, total=False):
    """One ranked item stored in the research packet."""

    title: str
    channel: str
    url: str
    source_class: str
    scores: ScoreBreakdown
    features: ItemFeatures
    one_line_takeaway: str
    transcript: str


class SourceValidationSummary(TypedDict):
    """Aggregate source-validation counts stored in the packet."""

    validated: int
    partially: int
    unverified: int
    low_trust: int
    primary: int
    secondary: int
    commentary: int
    notes: str


class StatsSummary(TypedDict):
    """Top-level statistical summary attached to the packet."""

    models_run: list[str]
    highlights: list[str]
    low_confidence: bool


class ResponseSchema(TypedDict):
    """Skill-mode schema for the LLM-authored sections."""

    compiled_synthesis: str
    opportunity_analysis: str


class ResearchPacket(TypedDict):
    """Canonical single-topic research packet emitted by the pipeline."""

    topic: str
    platform: str
    purpose_set: list[str]
    items_top5: list[ScoredItem]
    source_validation_summary: SourceValidationSummary
    platform_signals_summary: str
    evidence_summary: str
    stats_summary: StatsSummary
    chart_captions: list[str]
    warnings: list[str]
    response_schema: ResponseSchema


class MultiResearchPacket(TypedDict):
    """Packet wrapper used when one request produces multiple topic packets."""

    multi: list[ResearchPacket]
    response_schema: ResponseSchema


PacketPayload: TypeAlias = ResearchPacket | MultiResearchPacket
