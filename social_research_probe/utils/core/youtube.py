"""YouTube-specific parsing helpers."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse


def _bare_youtube_video_id(value: object) -> str | None:
    if isinstance(value, str) and value and "/" not in value and "." not in value:
        return value
    return None


def _youtube_video_id_from_short_url(value: str) -> str | None:
    parsed = urlparse(value)
    host = (parsed.hostname or "").removeprefix("www.")
    if host != "youtu.be":
        return None
    return parsed.path.lstrip("/") or None


def _youtube_video_id_from_query(value: str) -> str | None:
    parsed = urlparse(value)
    return parse_qs(parsed.query).get("v", [None])[0]


def youtube_video_id_from_url(value: object) -> str | None:
    """Return a YouTube video id parsed from a URL-like value."""
    if not isinstance(value, str):
        return None
    return _youtube_video_id_from_query(value) or _youtube_video_id_from_short_url(value)


def youtube_video_id_from_item(item: dict) -> str | None:
    """Return the preferred YouTube video id from an item dict."""
    return _bare_youtube_video_id(item.get("id")) or youtube_video_id_from_url(item.get("url"))
