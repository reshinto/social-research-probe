"""Pure pipeline helper utilities."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from social_research_probe.utils.core.types import RawItem

T = TypeVar("T")


def normalize_item(item: object) -> dict | None:
    """Convert a RawItem or dict into a plain dict suitable for pipeline stages.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            normalize_item(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            {"enabled": True}
    """
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
    """Return True only when summary divergence has transcript text to compare against.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _has_real_transcript(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            True
    """
    status = item.get("transcript_status")
    if status is not None and status != "available":
        return False
    transcript = item.get("transcript")
    return isinstance(transcript, str) and bool(transcript.strip())


def dict_items(items: list) -> list[dict]:
    """Return only dict items from a heterogeneous item list.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            dict_items(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [item for item in items if isinstance(item, dict)]


def first_tech_output(
    result: object,
    output_type: type[T],
    *,
    require_success: bool = False,
    require_truthy: bool = False,
) -> T | None:
    """Return the first technology output matching the requested filters.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        result: Service or technology result being inspected for payload and diagnostics.
        output_type: Expected output class used when extracting typed service payloads.
        require_success: Flag that selects the branch for this operation.
        require_truthy: Flag that selects the branch for this operation.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            first_tech_output(
                result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                output_type=dict,
                require_success=True,
                require_truthy=True,
            )
        Output:
            "AI safety"
    """
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
    """Return divergence warning strings for items exceeding threshold.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        top_n: Ordered source items being carried through the current pipeline step.
        threshold: Numeric score, threshold, prior, or confidence value.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            collect_divergence_warnings(
                top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                threshold=0.75,
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Resolve the path from file uri path used by this command.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        uri: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            _path_from_file_uri(
                uri="https://youtu.be/abc123",
            )
        Output:
            Path("report.html")
    """
    from urllib.parse import unquote, urlparse

    return Path(unquote(urlparse(uri).path))


def _looks_like_filesystem_path(s: str) -> bool:
    """Resolve the looks like filesystem path path used by this command.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _looks_like_filesystem_path(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    return s.startswith("/") or s.startswith("./") or s.startswith("../")


def resolve_item_source_class(item: dict) -> dict:
    """Return item copy with source_class set by title signal or coerced from existing value.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            resolve_item_source_class(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            {"enabled": True}
    """
    from social_research_probe.utils.core.classifying import classify_by_title_signal, coerce_class

    enriched = dict(item)
    if classify_by_title_signal(str(item.get("title") or "")) == "commentary":
        enriched["source_class"] = "commentary"
    else:
        enriched["source_class"] = coerce_class(item.get("source_class"))
    return enriched


def apply_channel_classes(classified: list[dict], channel_classes: dict[str, str]) -> None:
    """Update source_class for any classified items still marked 'unknown'.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        classified: Intermediate collection used to preserve ordering while stage results are
                    merged.
        channel_classes: YouTube channel name, id, or classification map used for source labeling.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            apply_channel_classes(
                classified=[],
                channel_classes={"OpenAI": "primary"},
            )
        Output:
            None
    """
    for item in classified:
        if item.get("source_class") != "unknown":
            continue
        channel = str(item.get("channel") or item.get("author_name") or "")
        item["source_class"] = channel_classes.get(channel, "unknown")


def resolve_html_report_path(report: dict) -> Path | None:
    """Return filesystem Path for the HTML report, or None if unavailable.

    Checks html_report_path (file:// URI) first, then report_path (plain filesystem path from
    markdown fallback only — not serve command strings).

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            resolve_html_report_path(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            Path("report.html")
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
