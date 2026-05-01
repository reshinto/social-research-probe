"""Build normalized text evidence for downstream enrichment.

The pipeline receives heterogeneous item dictionaries: some have transcripts,
some only have platform metadata, and future sources may add comments or web
snippets. This service turns those loose fields into a ``TextSurrogate``: a
small evidence contract that tells summarisation which text to use, tells
reporting how strong the evidence is, and records why confidence may be lower.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.utils.core.types import EvidenceTier, TextSurrogate

_PLATFORM_DOMAINS: dict[str, str] = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
}

_TRANSCRIPT_WARNING_STATUSES = frozenset(
    {"failed", "timeout", "provider_blocked"},
)


class TextSurrogateService(BaseService[dict, TextSurrogate]):
    """Construct deterministic text-evidence records from enriched item dictionaries.

    Unlike transcript or summary services, this service does not call external
    technologies. It still inherits from ``BaseService`` so enrichment services
    follow one lifecycle and naming convention across the pipeline.
    """

    service_name = "text_surrogate"
    enabled_config_key = "services.youtube.enriching.text_surrogate"

    def _get_technologies(self) -> list[object]:
        """Return no technologies because surrogate construction is local and deterministic."""
        return [None]

    async def execute_service(self, data: dict, result: ServiceResult) -> ServiceResult:
        """Build one surrogate and wrap it in the standard service result shape.

        ``TextSurrogateService`` has no external technology calls, but it still
        runs inside the protected service lifecycle so gates, result handling, and
        tests follow the same pattern as other enrichment services.
        """
        surrogate = self.from_item(data)
        return ServiceResult(
            service_name=self.service_name,
            input_key=repr(data),
            tech_results=[
                TechResult(
                    tech_name="text_surrogate_builder",
                    input=data,
                    output=surrogate,
                    success=True,
                )
            ],
        )

    def from_item(self, item: dict) -> TextSurrogate:
        """Build the evidence record used to route text into downstream analysis.

        The surrogate keeps the original item dict lightweight while providing one
        canonical place to choose primary text, evidence tier, and confidence flags.
        """
        url = item.get("url") or ""
        title = item.get("title") or ""
        description = item.get("text_excerpt") or item.get("description") or ""
        transcript = item.get("transcript") or ""
        transcript_status = item.get("transcript_status") or "not_attempted"
        comments: list[str] = item.get("comments") or []
        external_snippets: list[str] = item.get("external_snippets") or []

        primary_text, primary_text_source = _pick_primary(
            transcript,
            description,
            title,
        )
        layers = _build_layers(title, description, transcript, comments, external_snippets)
        tier = self.tier_from_layers(layers)
        penalties = _build_penalties(transcript, description)
        warnings = _build_warnings(transcript_status)

        return TextSurrogate(
            source_id=item.get("id") or "",
            platform=_detect_platform(url),
            url=url,
            title=title,
            description=description,
            channel_or_author=item.get("channel") or item.get("author_name") or "",
            published_at=_coerce_published_at(item.get("published_at")),
            comments=comments,
            transcript=transcript,
            transcript_status=transcript_status,
            external_snippets=external_snippets,
            primary_text=primary_text,
            primary_text_source=primary_text_source,
            evidence_layers=layers,
            evidence_tier=tier,
            confidence_penalties=penalties,
            warnings=warnings,
            char_count=len(primary_text),
        )

    def tier_from_layers(self, layers: list[str]) -> EvidenceTier:
        """Derive the reporting tier from the list of available evidence layers."""
        has_transcript = "transcript" in layers
        has_comments = "comments" in layers
        has_external = "external_snippets" in layers

        if has_transcript and has_comments and has_external:
            return "full"
        if has_transcript and has_comments:
            return "metadata_comments_transcript"
        if has_transcript:
            return "metadata_transcript"
        if has_comments:
            return "metadata_comments"
        if has_external:
            return "metadata_external"
        return "metadata_only"


def _pick_primary(transcript: str, description: str, title: str) -> tuple[str, str]:
    # Prefer full transcript text, then metadata text, so summaries are generated
    # from the richest available evidence without dropping items that lack transcripts.
    if transcript:
        return transcript, "transcript"
    if description:
        return description, "description"
    return title, "title"


def _build_layers(
    title: str,
    description: str,
    transcript: str,
    comments: list[str],
    external_snippets: list[str],
) -> list[str]:
    layers: list[str] = []
    if title:
        layers.append("title")
    if description:
        layers.append("description")
    if transcript:
        layers.append("transcript")
    if comments:
        layers.append("comments")
    if external_snippets:
        layers.append("external_snippets")
    return layers


def _build_penalties(transcript: str, description: str) -> list[str]:
    penalties: list[str] = []
    if not transcript:
        penalties.append("no_transcript")
    if not description:
        penalties.append("no_description")
    return penalties


def _build_warnings(transcript_status: str) -> list[str]:
    if transcript_status in _TRANSCRIPT_WARNING_STATUSES:
        return [f"transcript_{transcript_status}"]
    return []


def _detect_platform(url: str) -> str:
    if not url:
        return ""
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return _PLATFORM_DOMAINS.get(host, "")


def _coerce_published_at(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return ""
