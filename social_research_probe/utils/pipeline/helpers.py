"""Pure pipeline helper utilities."""

from __future__ import annotations

from pathlib import Path
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


def _path_from_file_uri(uri: str) -> Path:
    from urllib.parse import unquote, urlparse

    return Path(unquote(urlparse(uri).path))


def _looks_like_filesystem_path(s: str) -> bool:
    return s.startswith("/") or s.startswith("./") or s.startswith("../")


def resolve_item_source_class(item: dict) -> dict:
    """Return item copy with source_class set by title signal or coerced from existing value."""
    from social_research_probe.utils.core.classifying import classify_by_title_signal, coerce_class

    enriched = dict(item)
    if classify_by_title_signal(str(item.get("title") or "")) == "commentary":
        enriched["source_class"] = "commentary"
    else:
        enriched["source_class"] = coerce_class(item.get("source_class"))
    return enriched


def apply_channel_classes(classified: list[dict], channel_classes: dict[str, str]) -> None:
    """Update source_class for any classified items still marked 'unknown'."""
    for item in classified:
        if item.get("source_class") != "unknown":
            continue
        channel = str(item.get("channel") or item.get("author_name") or "")
        item["source_class"] = channel_classes.get(channel, "unknown")


def resolve_html_report_path(report: dict) -> Path | None:
    """Return filesystem Path for the HTML report, or None if unavailable.

    Checks html_report_path (file:// URI) first, then report_path (plain
    filesystem path from markdown fallback only — not serve command strings).
    """
    for field in ("html_report_path", "report_path"):
        raw = report.get(field)
        if not raw:
            continue
        if isinstance(raw, Path):
            return raw
        s = str(raw)
        if s.startswith("file://"):
            return _path_from_file_uri(s)
        if _looks_like_filesystem_path(s):
            return Path(s)
    return None
