"""YouTube-specific parsing helpers."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def _bare_youtube_video_id(value: object) -> str | None:
    """Return the bare YouTube video ID.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _bare_youtube_video_id(
                value="42",
            )
        Output:
            "AI safety"
    """
    if isinstance(value, str) and value and "/" not in value and "." not in value:
        return value
    return None


def _youtube_video_id_from_short_url(value: str) -> str | None:
    """Return the YouTube video ID from short URL.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _youtube_video_id_from_short_url(
                value="42",
            )
        Output:
            "AI safety"
    """
    parsed = urlparse(value)
    host = (parsed.hostname or "").removeprefix("www.")
    if host != "youtu.be":
        return None
    return parsed.path.lstrip("/") or None


def _youtube_video_id_from_query(value: str) -> str | None:
    """Document the youtube video id from query rule at the boundary where callers use it.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _youtube_video_id_from_query(
                value="42",
            )
        Output:
            "AI safety"
    """
    parsed = urlparse(value)
    return parse_qs(parsed.query).get("v", [None])[0]


def youtube_video_id_from_url(value: object) -> str | None:
    """Return a YouTube video id parsed from a URL-like value.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            youtube_video_id_from_url(
                value="42",
            )
        Output:
            "AI safety"
    """
    if not isinstance(value, str):
        return None
    return _youtube_video_id_from_query(value) or _youtube_video_id_from_short_url(value)


def youtube_video_id_from_item(item: dict) -> str | None:
    """Return the preferred YouTube video id from an item dict.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            youtube_video_id_from_item(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            "AI safety"
    """
    return _bare_youtube_video_id(item.get("id")) or youtube_video_id_from_url(item.get("url"))
