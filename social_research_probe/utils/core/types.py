"""Shared typed dicts and aliases used across configuration, state, and reports.

This module exists to keep the codebase on one vocabulary for the major nested
payloads that move between config loading, state storage, pipeline processing,
and rendering. The goal is not perfect static modelling of every dynamic field;
the goal is to remove vague untyped annotations and replace them with stable,
reviewable shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeAlias, TypedDict

from social_research_probe.utils.claims.types import ExtractedClaim

JSONScalar: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]

MetricValue: TypeAlias = None | bool | int | float | str
MetricMap: TypeAlias = dict[str, MetricValue]


@dataclass(frozen=True)
class FetchLimits:
    """Search-time fetch limits shared by all platform adapters.

    Examples:
        Input:
            FetchLimits
        Output:
            FetchLimits
    """

    max_items: int = 20
    recency_days: int | None = 90


@dataclass(frozen=True)
class RawItem:
    """Normalised raw content item returned by a platform adapter.

    Examples:
        Input:
            RawItem
        Output:
            RawItem
    """

    id: str
    url: str
    title: str
    author_id: str
    author_name: str
    published_at: datetime
    metrics: MetricMap
    text_excerpt: str | None
    thumbnail: str | None
    extras: MetricMap


@dataclass(frozen=True)
class EngagementMetrics:
    """Derived numeric signals computed from one or more raw items.

    Examples:
        Input:
            EngagementMetrics
        Output:
            EngagementMetrics
    """

    views: int | None
    likes: int | None
    comments: int | None
    upload_date: datetime | None
    view_velocity: float | None
    engagement_ratio: float | None
    comment_velocity: float | None
    cross_channel_repetition: float | None
    raw: MetricMap = field(default_factory=dict)


RunnerName = Literal["none", "claude", "gemini", "codex", "local"]
FreeTextRunnerName = Literal["claude", "gemini", "codex", "local"]


class RunnerSettings(TypedDict, total=False):
    """Per-runner CLI settings loaded from config.toml.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            RunnerSettings
        Output:
            {"title": "Example"}
    """

    binary: str
    extra_flags: list[str]


class LLMConfigSection(TypedDict):
    """Top-level [llm] config section with per-runner nested settings.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            LLMConfigSection
        Output:
            {"enabled": True}
    """

    runner: RunnerName
    timeout_seconds: int
    claude: RunnerSettings
    gemini: RunnerSettings
    codex: RunnerSettings
    local: RunnerSettings


class CorroborationConfigSection(TypedDict):
    """Top-level corroboration settings.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            CorroborationConfigSection
        Output:
            {"enabled": True}
    """

    provider: str
    max_claims_per_item: int
    max_claims_per_session: int


CommentsStatus: TypeAlias = Literal[
    "not_attempted",
    "available",
    "unavailable",
    "failed",
    "disabled",
]


class SourceComment(TypedDict, total=False):
    """One fetched top-level YouTube comment.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            SourceComment
        Output:
            {"text": "Useful point", "like_count": 3}
    """

    source_id: str
    platform: str
    comment_id: str
    author: str
    text: str
    like_count: int
    published_at: str


class CommentsConfig(TypedDict, total=False):
    """Per-platform comment-fetch configuration.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            CommentsConfig
        Output:
            {"text": "Useful point", "like_count": 3}
    """

    enabled: bool
    max_videos: int
    max_comments_per_video: int
    order: str


class ClaimsConfig(TypedDict, total=False):
    """Per-platform claim extraction configuration.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ClaimsConfig
        Output:
            {"enabled": True}
    """

    enabled: bool
    max_claims_per_source: int
    use_llm: bool
    max_claim_chars: int


class ExportConfig(TypedDict, total=False):
    """Per-platform export artifact configuration.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ExportConfig
        Output:
            {"enabled": True}
    """

    enabled: bool
    sources_csv: bool
    comments_csv: bool
    claims_csv: bool
    methodology_md: bool
    run_summary_json: bool


class YouTubePlatformConfig(TypedDict, total=False):
    """Configurable defaults for the YouTube adapter.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            YouTubePlatformConfig
        Output:
            {"enabled": True}
    """

    recency_days: int
    max_items: int
    enrich_top_n: int
    comments: CommentsConfig
    claims: ClaimsConfig
    export: ExportConfig


class PlatformsConfigSection(TypedDict):
    """Current platform defaults keyed by platform name.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PlatformsConfigSection
        Output:
            {"enabled": True}
    """

    youtube: YouTubePlatformConfig


class ScoringConfigSection(TypedDict):
    """Scoring config section with optional weight overrides.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ScoringConfigSection
        Output:
            {"enabled": True}
    """

    weights: dict[str, float]


StagesConfigSection = dict[str, dict[str, bool]]


class FetchServices(TypedDict, total=False):
    """Fetch services type.

    Examples:
        Input:
            FetchServices
        Output:
            {"title": "Example"}
    """

    platform_api: bool


class ScoreServices(TypedDict, total=False):
    """Score services type.

    Examples:
        Input:
            ScoreServices
        Output:
            {"title": "Example"}
    """

    scoring: bool


class EnrichServices(TypedDict, total=False):
    """Enrich services type.

    Examples:
        Input:
            EnrichServices
        Output:
            {"title": "Example"}
    """

    transcripts: bool
    text_surrogate: bool
    llm: bool
    media_url_summary: bool
    merged_summary: bool
    comments: bool


class CorroborateServices(TypedDict, total=False):
    """Corroborate services type.

    Examples:
        Input:
            CorroborateServices
        Output:
            {"title": "Example"}
    """

    corroboration: bool


class AnalyzeServices(TypedDict, total=False):
    """Analyze services type.

    Examples:
        Input:
            AnalyzeServices
        Output:
            {"title": "Example"}
    """

    statistics: bool
    charts: bool
    chart_takeaways: bool


class ReportServices(TypedDict, total=False):
    """Report services type.

    Examples:
        Input:
            ReportServices
        Output:
            {"title": "Example"}
    """

    html: bool
    audio: bool
    export: bool


class PersistenceServices(TypedDict, total=False):
    """Service gates for persistence backends.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PersistenceServices
        Output:
            {"title": "Example"}
    """

    sqlite: bool


class ServicesConfigSection(TypedDict, total=False):
    """Service-level gates applied after stage gates.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ServicesConfigSection
        Output:
            {"enabled": True}
    """

    fetch: FetchServices
    score: ScoreServices
    enrich: EnrichServices
    corroborate: CorroborateServices
    analyze: AnalyzeServices
    report: ReportServices
    persistence: PersistenceServices


class TechnologiesConfigSection(TypedDict):
    """Technology/provider gates applied after stage and service gates.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            TechnologiesConfigSection
        Output:
            {"enabled": True}
    """

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
    youtube_comments: bool
    export_package: bool
    sqlite_persist: bool


class DatabaseConfigSection(TypedDict, total=False):
    """Local SQLite persistence settings.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            DatabaseConfigSection
        Output:
            {"enabled": True}
    """

    enabled: bool
    path: str
    persist_transcript_text: bool
    persist_comment_text: bool


class TunablesConfigSection(TypedDict):
    """Numeric tunables with no on/off semantics.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            TunablesConfigSection
        Output:
            {"enabled": True}
    """

    summary_divergence_threshold: float
    per_item_summary_words: int


class DebugConfigSection(TypedDict):
    """Technology-call logging switches. Default False; env SRP_LOGS overrides.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            DebugConfigSection
        Output:
            {"enabled": True}
    """

    technology_logs_enabled: bool


class VoiceboxConfigSection(TypedDict):
    """Voicebox renderer defaults stored in config.toml.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            VoiceboxConfigSection
        Output:
            {"enabled": True}
    """

    default_profile_name: str
    api_base: str


class NotificationConsoleConfig(TypedDict, total=False):
    """Console notification channel settings."""

    enabled: bool


class NotificationFileConfig(TypedDict, total=False):
    """Local file notification channel settings."""

    enabled: bool
    output_dir: str


class NotificationTelegramConfig(TypedDict, total=False):
    """Telegram notification channel settings.

    Secret values are never stored here; only environment variable names are configured.
    """

    enabled: bool
    bot_token_env: str
    chat_id_env: str
    timeout_seconds: int


class NotificationsConfigSection(TypedDict, total=False):
    """Top-level local notification settings."""

    enabled: bool
    default_channels: list[str]
    console: NotificationConsoleConfig
    file: NotificationFileConfig
    telegram: NotificationTelegramConfig


class ScheduleConfigSection(TypedDict, total=False):
    """Local schedule helper settings."""

    enabled: bool
    default_interval: str


class AppConfig(TypedDict):
    """Canonical in-memory shape of config.toml after defaults are applied.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            AppConfig
        Output:
            {"enabled": True}
    """

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
    database: DatabaseConfigSection
    notifications: NotificationsConfigSection
    schedule: ScheduleConfigSection


class AdapterConfig(TypedDict, total=False):
    """Runtime adapter config assembled from file defaults plus CLI overrides.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            AdapterConfig
        Output:
            {"enabled": True}
    """

    data_dir: Path
    include_shorts: bool
    fetch_transcripts: bool
    recency_days: int
    max_items: int
    enrich_top_n: int


class PurposeEntry(TypedDict):
    """One persisted purpose entry from purposes.json.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PurposeEntry
        Output:
            {"title": "Example"}
    """

    method: str
    evidence_priorities: list[str]
    scoring_overrides: dict[str, float]


class TopicsState(TypedDict):
    """Persisted topics.json structure.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            TopicsState
        Output:
            {"title": "Example"}
    """

    schema_version: int
    topics: list[str]


class PurposesState(TypedDict):
    """Persisted purposes.json structure.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PurposesState
        Output:
            {"title": "Example"}
    """

    schema_version: int
    purposes: dict[str, PurposeEntry]


DuplicateStatusValue = Literal["new", "near-duplicate", "duplicate"]


class PendingTopicSuggestion(TypedDict):
    """One staged topic suggestion.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PendingTopicSuggestion
        Output:
            {"title": "Example"}
    """

    id: int
    value: str
    reason: str
    duplicate_status: DuplicateStatusValue
    matches: list[str]


class PendingPurposeSuggestion(TypedDict):
    """One staged purpose suggestion.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PendingPurposeSuggestion
        Output:
            {"title": "Example"}
    """

    id: int
    name: str
    method: str
    evidence_priorities: list[str]
    duplicate_status: DuplicateStatusValue
    matches: list[str]


class PendingSuggestionsState(TypedDict):
    """Persisted pending_suggestions.json structure.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PendingSuggestionsState
        Output:
            {"title": "Example"}
    """

    schema_version: int
    pending_topic_suggestions: list[PendingTopicSuggestion]
    pending_purpose_suggestions: list[PendingPurposeSuggestion]


class TopicSuggestionCandidate(TypedDict, total=False):
    """Unpersisted topic suggestion candidate before staging.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            TopicSuggestionCandidate
        Output:
            {"title": "Example"}
    """

    value: str
    reason: str


class PurposeSuggestionCandidate(TypedDict, total=False):
    """Unpersisted purpose suggestion candidate before staging.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            PurposeSuggestionCandidate
        Output:
            {"title": "Example"}
    """

    name: str
    method: str
    evidence_priorities: list[str]


class ScoreBreakdown(TypedDict):
    """Per-item score breakdown used by the report renderer.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ScoreBreakdown
        Output:
            {"title": "Example"}
    """

    trust: float
    trend: float
    opportunity: float
    overall: float


class ItemFeatures(TypedDict):
    """Derived numeric features that downstream stats and charts consume.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ItemFeatures
        Output:
            {"title": "Example"}
    """

    view_velocity: float
    engagement_ratio: float
    age_days: float
    subscriber_count: float


TranscriptStatus: TypeAlias = Literal[
    "not_attempted",
    "available",
    "unavailable",
    "failed",
    "timeout",
    "provider_blocked",
    "disabled",
]

EvidenceTier: TypeAlias = Literal[
    "metadata_only",
    "metadata_comments",
    "metadata_transcript",
    "metadata_comments_transcript",
    "metadata_external",
    "full",
]


class TextSurrogate(TypedDict, total=False):
    """Evidence collected for a single item.

    This is the handoff contract between enrichment, LLM summarisation, scoring, and rendering: it
    selects the best available text while recording the evidence layers and limitations present at
    analysis time.

    Examples:
        Input:
            TextSurrogate
        Output:
            {"title": "Example"}
    """

    source_id: str
    platform: str
    url: str
    title: str
    description: str
    channel_or_author: str
    published_at: str
    comments: list[str]
    transcript: str
    transcript_status: TranscriptStatus
    external_snippets: list[str]
    primary_text: str
    primary_text_source: str
    evidence_layers: list[str]
    evidence_tier: EvidenceTier
    confidence_penalties: list[str]
    warnings: list[str]
    char_count: int


class ScoredItem(TypedDict, total=False):
    """One ranked item stored in the research report.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ScoredItem
        Output:
            {"title": "Example"}
    """

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
    transcript_status: TranscriptStatus
    evidence_tier: EvidenceTier
    text_surrogate: TextSurrogate
    corroboration_verdict: str
    comments_status: CommentsStatus
    source_comments: list[SourceComment]
    comments: list[str]
    extracted_claims: list[ExtractedClaim]


class SourceValidationSummary(TypedDict):
    """Aggregate source-validation counts stored in the report.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            SourceValidationSummary
        Output:
            {"title": "Example"}
    """

    validated: int
    partially: int
    unverified: int
    low_trust: int
    primary: int
    secondary: int
    commentary: int
    notes: str


class StatsSummary(TypedDict):
    """Top-level statistical summary attached to the report.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            StatsSummary
        Output:
            {"title": "Example"}
    """

    models_run: list[str]
    highlights: list[str]
    low_confidence: bool


class Coverage(TypedDict):
    """What the pipeline fetched vs. what it deeply analysed.

    Lets the synthesis LLM disclose scope (e.g. stats cover all fetched items but transcripts only
    the enriched top-N) instead of silently over-claiming.

    Examples:
        Input:
            Coverage
        Output:
            {"title": "Example"}
    """

    fetched: int
    enriched: int
    platforms: list[str]


class SynthesisItem(TypedDict, total=False):
    """Compact per-item card seen by the final synthesis LLM.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            SynthesisItem
        Output:
            {"title": "Example"}
    """

    rank: int
    title: str
    url: str
    scores: ScoreBreakdown
    takeaway: str
    summary: str
    corroboration: str


class SynthesisContext(TypedDict):
    """The exact shape passed to the synthesis prompt.

    Pure pass-through from ``ResearchReport`` — no LLM work, no recomputation, just the already-
    derived digests. Tolerates every optional upstream field being absent/empty so disabled features
    silently produce empty sections.

    Examples:
        Input:
            SynthesisContext
        Output:
            {"title": "Example"}
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
    """Canonical single-topic research report emitted by the pipeline.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ResearchReport
        Output:
            {"title": "Example"}
    """

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
    export_paths: dict[str, str]


class MultiResearchReport(TypedDict, total=False):
    """Report wrapper used when one request produces multiple topic reports.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            MultiResearchReport
        Output:
            {"title": "Example"}
    """

    multi: list[ResearchReport]
    html_report_path: str


ReportPayload: TypeAlias = ResearchReport | MultiResearchReport
