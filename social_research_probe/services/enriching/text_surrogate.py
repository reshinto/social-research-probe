"""Pure-function service that builds a TextSurrogate from an item dict."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from social_research_probe.utils.core.types import EvidenceTier, TextSurrogate

_PLATFORM_DOMAINS: dict[str, str] = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
}

_TRANSCRIPT_WARNING_STATUSES = frozenset(
    {"failed", "timeout", "provider_blocked"},
)


class TextSurrogateService:
    @staticmethod
    def from_item(item: dict) -> TextSurrogate:
        """Build a TextSurrogate from an item dict's available fields."""
        url = item.get("url") or ""
        title = item.get("title") or ""
        description = item.get("text_excerpt") or item.get("description") or ""
        transcript = item.get("transcript") or ""
        transcript_status = item.get("transcript_status") or "not_attempted"
        comments: list[str] = item.get("comments") or []
        external_snippets: list[str] = item.get("external_snippets") or []

        primary_text, primary_text_source = _pick_primary(
            transcript, description, title,
        )
        layers = _build_layers(title, description, transcript, comments, external_snippets)
        tier = TextSurrogateService.tier_from_layers(layers)
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

    @staticmethod
    def tier_from_layers(layers: list[str]) -> EvidenceTier:
        """Derive evidence tier from the list of available evidence layers."""
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
