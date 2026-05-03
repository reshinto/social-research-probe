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

    Unlike transcript or summary services, this service does not call external technologies. It
    still inherits from ``BaseService`` so enrichment services follow one lifecycle and naming
    convention across the pipeline.

    Examples:
        Input:
            TextSurrogateService
        Output:
            TextSurrogateService
    """

    service_name = "text_surrogate"
    enabled_config_key = "services.youtube.enriching.text_surrogate"

    def _get_technologies(self) -> list[object]:
        """Return no technologies because surrogate construction is local and deterministic.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _get_technologies()
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        return [None]

    async def execute_service(self, data: dict, result: ServiceResult) -> ServiceResult:
        """Build one surrogate and wrap it in the standard service result shape.

        ``TextSurrogateService`` has no external technology calls, but it still runs inside the
        protected service lifecycle so gates, result handling, and tests follow the same pattern as
        other enrichment services.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_service(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
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
        """Build a text surrogate from the transcript, description, title, and metadata on an item.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            item: Single source item, database row, or registry entry being transformed.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                from_item(
                    item={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
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
        """Choose an evidence tier from the source text layers that were available.

        Services turn platform items into adapter requests and normalize results so stages handle
        success, skip, and failure the same way.

        Args:
            layers: Evidence-layer records that describe which source text was available.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                tier_from_layers(
                    layers=[{"kind": "transcript", "available": True}],
                )
            Output:
                "AI safety"
        """
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
    """Choose the strongest available text source for summarization and claim extraction.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        transcript: Source text, prompt text, or raw value being parsed, normalized, classified, or
                    sent to a provider.
        description: Source text, prompt text, or raw value being parsed, normalized, classified, or
                     sent to a provider.
        title: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _pick_primary(
                transcript="This tool reduces latency by 30%.",
                description="This tool reduces latency by 30%.",
                title="This tool reduces latency by 30%.",
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
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
    """Build the layers structure consumed by the next step.

    Services turn platform items into adapter requests and normalize results so stages handle
    success, skip, and failure the same way.

    Args:
        title: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.
        description: Source text, prompt text, or raw value being parsed, normalized, classified, or
                     sent to a provider.
        transcript: Source text, prompt text, or raw value being parsed, normalized, classified, or
                    sent to a provider.
        comments: Comment records or text used as audience evidence.
        external_snippets: External evidence snippets collected from corroboration or search
                           providers.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _build_layers(
                title="This tool reduces latency by 30%.",
                description="This tool reduces latency by 30%.",
                transcript="This tool reduces latency by 30%.",
                comments=[{"text": "Useful point"}],
                external_snippets=["External source confirms the claim."],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Build the penalties structure consumed by the next step.

    Services turn platform items into adapter requests and normalize results so stages handle
    success, skip, and failure the same way.

    Args:
        transcript: Source text, prompt text, or raw value being parsed, normalized, classified, or
                    sent to a provider.
        description: Source text, prompt text, or raw value being parsed, normalized, classified, or
                     sent to a provider.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _build_penalties(
                transcript="This tool reduces latency by 30%.",
                description="This tool reduces latency by 30%.",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    penalties: list[str] = []
    if not transcript:
        penalties.append("no_transcript")
    if not description:
        penalties.append("no_description")
    return penalties


def _build_warnings(transcript_status: str) -> list[str]:
    """Build the warnings structure consumed by the next step.

    Services turn platform items into adapter requests and normalize results so stages handle
    success, skip, and failure the same way.

    Args:
        transcript_status: Lifecycle, evidence, or provider status being written into the output
                           record.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _build_warnings(
                transcript_status="available",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    if transcript_status in _TRANSCRIPT_WARNING_STATUSES:
        return [f"transcript_{transcript_status}"]
    return []


def _detect_platform(url: str) -> str:
    """Infer the source platform from a URL.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        url: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _detect_platform(
                url="https://youtu.be/abc123",
            )
        Output:
            "AI safety"
    """
    if not url:
        return ""
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return _PLATFORM_DOMAINS.get(host, "")


def _coerce_published_at(value: object) -> str:
    """Convert an untyped value into a safe published at value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _coerce_published_at(
                value="42",
            )
        Output:
            "AI safety"
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return ""
