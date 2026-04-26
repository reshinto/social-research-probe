"""Shared typed dicts and aliases used across configuration, state, and reports.

This module exists to keep the codebase on one vocabulary for the major nested
payloads that move between config loading, state storage, pipeline processing,
and rendering. The goal is not perfect static modelling of every dynamic field;
the goal is to remove vague untyped annotations and replace them with stable,
reviewable shapes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypeAlias, TypedDict

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

    provider: str
    max_claims_per_item: int
    max_claims_per_session: int


class YouTubePlatformConfig(TypedDict, total=False):
    """Configurable defaults for the YouTube adapter."""

    recency_days: int
    max_items: int
    enrich_top_n: int
    cache_ttl_search_hours: int
    cache_ttl_channel_hours: int


class PlatformsConfigSection(TypedDict):
    """Current platform defaults keyed by platform name."""

    youtube: YouTubePlatformConfig


class ScoringConfigSection(TypedDict):
    """Scoring config section with optional weight overrides."""

    weights: dict[str, float]


StagesConfigSection = dict[str, dict[str, bool]]


class FetchServices(TypedDict, total=False):
    platform_api: bool


class ScoreServices(TypedDict, total=False):
    scoring: bool


class EnrichServices(TypedDict, total=False):
    transcripts: bool
    llm: bool
    media_url_summary: bool
    merged_summary: bool


class CorroborateServices(TypedDict, total=False):
    corroboration: bool


class AnalyzeServices(TypedDict, total=False):
    statistics: bool
    charts: bool
    chart_takeaways: bool


class ReportServices(TypedDict, total=False):
    html: bool
    audio: bool


class ServicesConfigSection(TypedDict, total=False):
    """Service-level gates applied after stage gates."""

    fetch: FetchServices
    score: ScoreServices
    enrich: EnrichServices
    corroborate: CorroborateServices
    analyze: AnalyzeServices
    report: ReportServices


class TechnologiesConfigSection(TypedDict):
    """Technology/provider gates applied after stage and service gates."""

    youtube_api: bool
    youtube_transcript_api: bool
    whisper: bool
    voicebox: bool
    claude: bool
    gemini: bool
    codex: bool
    local: bool
    llm_search: bool
    exa: bool
    brave: bool
    tavily: bool


class TunablesConfigSection(TypedDict):
    """Numeric tunables with no on/off semantics."""

    summary_divergence_threshold: float
    per_item_summary_words: int


class DebugConfigSection(TypedDict):
    """Technology-call logging switches. Default False; env SRP_LOGS overrides."""

    technology_logs_enabled: bool


class VoiceboxConfigSection(TypedDict):
    """Voicebox renderer defaults stored in config.toml."""

    default_profile_name: str


class AppConfig(TypedDict):
    """Canonical in-memory shape of config.toml after defaults are applied."""

    llm: LLMConfigSection
    corroboration: CorroborationConfigSection
    platforms: PlatformsConfigSection
    scoring: ScoringConfigSection
    stages: StagesConfigSection
    services: ServicesConfigSection
    technologies: TechnologiesConfigSection
    tunables: TunablesConfigSection
    debug: DebugConfigSection
    voicebox: VoiceboxConfigSection


class AdapterConfig(TypedDict, total=False):
    """Runtime adapter config assembled from file defaults plus CLI overrides."""

    data_dir: Path
    include_shorts: bool
    fetch_transcripts: bool
    recency_days: int
    max_items: int
    enrich_top_n: int
    cache_ttl_search_hours: int
    cache_ttl_channel_hours: int


class PurposeEntry(TypedDict):
    """One persisted purpose entry from purposes.json."""

    method: str
    evidence_priorities: list[str]
    scoring_overrides: dict[str, float]


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
    """Per-item score breakdown used by the report renderer."""

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
    """One ranked item stored in the research report."""

    title: str
    channel: str
    url: str
    source_class: str
    scores: ScoreBreakdown
    features: ItemFeatures
    one_line_takeaway: str
    summary: str
    url_summary: str
    summary_divergence: float
    summary_source: str
    transcript: str
    corroboration_verdict: str


class SourceValidationSummary(TypedDict):
    """Aggregate source-validation counts stored in the report."""

    validated: int
    partially: int
    unverified: int
    low_trust: int
    primary: int
    secondary: int
    commentary: int
    notes: str


class StatsSummary(TypedDict):
    """Top-level statistical summary attached to the report."""

    models_run: list[str]
    highlights: list[str]
    low_confidence: bool


class Coverage(TypedDict):
    """What the pipeline fetched vs. what it deeply analysed.

    Lets the synthesis LLM disclose scope (e.g. stats cover all fetched items
    but transcripts only the enriched top-N) instead of silently over-claiming.
    """

    fetched: int
    enriched: int
    platforms: list[str]


class SynthesisItem(TypedDict, total=False):
    """Compact per-item card seen by the final synthesis LLM."""

    rank: int
    title: str
    url: str
    scores: ScoreBreakdown
    takeaway: str
    summary: str
    corroboration: str


class SynthesisContext(TypedDict):
    """The exact shape passed to the synthesis prompt.

    Pure pass-through from ``ResearchReport`` — no LLM work, no recomputation,
    just the already-derived digests. Tolerates every optional upstream field
    being absent/empty so disabled features silently produce empty sections.
    """

    topic: str
    platform: str
    coverage: Coverage
    items: list[SynthesisItem]
    source_validation_summary: SourceValidationSummary
    platform_engagement_summary: str
    evidence_summary: str
    stats_highlights: list[str]
    chart_takeaways: list[str]
    warnings: list[str]


class ResearchReport(TypedDict, total=False):
    """Canonical single-topic research report emitted by the pipeline."""

    topic: str
    platform: str
    purpose_set: list[str]
    items_top_n: list[ScoredItem]
    source_validation_summary: SourceValidationSummary
    platform_engagement_summary: str
    evidence_summary: str
    stats_summary: StatsSummary
    chart_captions: list[str]
    chart_takeaways: list[str]
    warnings: list[str]
    stage_timings: list[dict]
    compiled_synthesis: str
    opportunity_analysis: str
    report_summary: str
    html_report_path: str


class MultiResearchReport(TypedDict, total=False):
    """Report wrapper used when one request produces multiple topic reports."""

    multi: list[ResearchReport]
    html_report_path: str


ReportPayload: TypeAlias = ResearchReport | MultiResearchReport
