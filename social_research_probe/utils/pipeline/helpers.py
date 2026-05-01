"""Pure pipeline helper utilities."""

from __future__ import annotations

from typing import TypeVar

from social_research_probe.utils.core.types import RawItem

T = TypeVar("T")


def normalize_item(item: object) -> dict | None:
    """Convert a RawItem or dict into a plain dict suitable for pipeline stages."""
    if isinstance(item, dict):
        return item
    if not isinstance(item, RawItem):
        return None
    return {
        "id": item.id,
        "url": item.url,
        "title": item.title,
        "channel": item.author_name,
        "author_id": item.author_id,
        "author_name": item.author_name,
        "published_at": item.published_at,
        "text_excerpt": item.text_excerpt,
        "thumbnail": item.thumbnail,
        "extras": dict(item.extras) if item.extras else {},
    }


def _has_real_transcript(item: dict) -> bool:
    """Return True only when summary divergence has transcript text to compare against."""
    status = item.get("transcript_status")
    if status is not None and status != "available":
        return False
    transcript = item.get("transcript")
    return isinstance(transcript, str) and bool(transcript.strip())


def dict_items(items: list) -> list[dict]:
    """Return only dict items from a heterogeneous item list."""
    return [item for item in items if isinstance(item, dict)]


def first_tech_output(
    result: object,
    output_type: type[T],
    *,
    require_success: bool = False,
    require_truthy: bool = False,
) -> T | None:
    """Return the first technology output matching the requested filters."""
    for tech_result in getattr(result, "tech_results", []):
        if require_success and not getattr(tech_result, "success", False):
            continue
        output = getattr(tech_result, "output", None)
        if require_truthy and not output:
            continue
        if isinstance(output, output_type):
            return output
    return None


def collect_divergence_warnings(top_n: list, threshold: float) -> list[str]:
    """Return divergence warning strings for items exceeding threshold."""
    warnings: list[str] = []
    for item in top_n:
        if not isinstance(item, dict):
            continue
        if not _has_real_transcript(item):
            continue
        divergence = item.get("summary_divergence")
        if divergence is not None and divergence > threshold:
            title = (item.get("title") or "untitled")[:80]
            warnings.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")
    return warnings
