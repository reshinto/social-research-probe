"""google-api-python-client wrappers. Real calls; tests don't import this."""

from __future__ import annotations

from collections.abc import Mapping

from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.core.types import JSONObject, JSONValue
from social_research_probe.utils.display.progress import log_with_time


_ENV_KEY = "SRP_YOUTUBE_API_KEY"
_SECRET_KEY = "youtube_api_key"


def _build_client(api_key: str):
    """Build a YouTube Data API v3 client."""
    from googleapiclient.discovery import build

    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def _items_from_response(response: Mapping[str, JSONValue]) -> list[JSONObject]:
    """Extract object items from a YouTube API response.

    Args:
        response: Raw YouTube API response payload. Expected to contain an
            ``items`` field with a list of JSON objects.

    Returns:
        A list containing only dictionary items from ``response["items"]``.
        Returns an empty list when ``items`` is missing, not a list, or contains
        no object values.
    """
    items = response.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _search_videos(
    api_key: str,
    *,
    topic: str,
    max_items: int,
    published_after: str | None,
) -> list[JSONObject]:
    """Search YouTube videos for a topic.

    Args:
        api_key: YouTube Data API key.
        topic: Search query string to send as the YouTube ``q`` parameter.
        max_items: Maximum number of videos to request. Values above 50 are
            capped at 50 because ``search.list`` allows at most 50 results per
            request.
        published_after: Optional RFC 3339 datetime string used as the
            YouTube ``publishedAfter`` filter, or ``None`` for no date filter.

    Returns:
        Raw JSON objects from the YouTube ``search.list`` response ``items``
        field. Each item is expected to describe a matching video search result.

    Raises:
        AdapterError: If the YouTube API request fails.
    """
    client = _build_client(api_key)
    try:
        resp = (
            client.search()
            .list(
                q=topic,
                part="snippet",
                type="video",
                maxResults=min(50, max_items),
                publishedAfter=published_after,
                order="relevance",
            )
            .execute()
        )
    except Exception as exc:
        raise AdapterError(f"youtube search failed: {exc}") from exc
    return _items_from_response(resp)


def _fetch_video_details(api_key: str, *, video_ids: list[str]) -> list[JSONObject]:
    """Fetch details for YouTube videos by id.

    Args:
        api_key: YouTube Data API key.
        video_ids: YouTube video ids to hydrate. Expected to be plain video id
            strings, not full URLs.

    Returns:
        Raw JSON objects from the YouTube ``videos.list`` response ``items``
        field. Each item may include ``snippet``, ``statistics``, and
        ``contentDetails`` data.

    Raises:
        AdapterError: If the YouTube API request fails.
    """
    client = _build_client(api_key)
    try:
        resp = (
            client.videos()
            .list(
                id=",".join(video_ids),
                part="snippet,statistics,contentDetails",
            )
            .execute()
        )
    except Exception as exc:
        raise AdapterError(f"youtube videos.list failed: {exc}") from exc
    return _items_from_response(resp)


def _fetch_channel_details(api_key: str, *, channel_ids: list[str]) -> list[JSONObject]:
    """Fetch details for YouTube channels by id.

    Args:
        api_key: YouTube Data API key.
        channel_ids: YouTube channel ids to hydrate. Expected to be plain
            channel id strings.

    Returns:
        Raw JSON objects from the YouTube ``channels.list`` response ``items``
        field. Each item may include ``snippet``, ``statistics``, and
        ``brandingSettings`` data.

    Raises:
        AdapterError: If the YouTube API request fails.
    """
    client = _build_client(api_key)
    try:
        resp = (
            client.channels()
            .list(
                id=",".join(channel_ids),
                part="snippet,statistics,brandingSettings",
            )
            .execute()
        )
    except Exception as exc:
        raise AdapterError(f"youtube channels.list failed: {exc}") from exc
    return _items_from_response(resp)


def resolve_youtube_api_key() -> str:
    """Resolve the YouTube API key from env or secrets store.

    Raises:
        AdapterError: If no API key is available.
    """
    import os

    from social_research_probe.commands.config import read_secret

    key = os.environ.get(_ENV_KEY) or read_secret(_SECRET_KEY)
    if key:
        return key
    raise AdapterError(
        f"{_SECRET_KEY} missing — run `srp config set-secret {_SECRET_KEY}` in a terminal"
    )


def youtube_health_check() -> bool:
    """Return True when the YouTube API key can be resolved."""
    resolve_youtube_api_key()
    return True


@log_with_time("[srp] youtube: search {topic!r} max={max_items}")
def search_youtube(
    topic: str,
    *,
    max_items: int,
    published_after: str | None = None,
) -> list[JSONObject]:
    """Search YouTube using configured credentials.

    Args:
        topic: Search query string.
        max_items: Maximum number of videos to request. Values above 50 are
            capped by ``_search_videos``.
        published_after: Optional RFC 3339 datetime string used to filter out
            videos published before that time.

    Returns:
        Raw JSON objects from the YouTube ``search.list`` response ``items``
        field.

    Raises:
        AdapterError: If credentials are missing or the API request fails.
    """
    return _search_videos(
        resolve_youtube_api_key(),
        topic=topic,
        max_items=max_items,
        published_after=published_after,
    )


@log_with_time("[srp] youtube: hydrate")
async def hydrate_youtube(
    video_ids: list[str],
    channel_ids: list[str],
) -> tuple[list[JSONObject], list[JSONObject]]:
    """Fetch YouTube video and channel details concurrently.

    Args:
        video_ids: YouTube video ids to hydrate.
        channel_ids: YouTube channel ids to hydrate.

    Returns:
        A tuple ``(videos, channels)`` where ``videos`` contains raw
        ``videos.list`` item objects and ``channels`` contains raw
        ``channels.list`` item objects.

    Raises:
        AdapterError: If credentials are missing or either API request fails.
    """
    import asyncio

    api_key = resolve_youtube_api_key()
    return await asyncio.gather(
        asyncio.to_thread(_fetch_video_details, api_key, video_ids=video_ids),
        asyncio.to_thread(_fetch_channel_details, api_key, channel_ids=channel_ids),
    )
