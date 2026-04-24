"""google-api-python-client wrappers. Real calls; tests don't import this."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, Protocol

from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.core.types import JSONObject, JSONValue
from social_research_probe.utils.display.progress import log


def build_client(api_key: str):
    from googleapiclient.discovery import build

    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


class _ExecutableRequest(Protocol):
    """Protocol for google-api-python-client request objects."""

    def execute(self) -> Mapping[str, JSONValue]:
        """Return the decoded API response payload."""


class _ListResource(Protocol):
    """Protocol for resource wrappers exposing a .list(...).execute() chain."""

    def list(self, **_kwargs: object) -> _ExecutableRequest:
        """Build a request object for one API call."""


class YouTubeClient(Protocol):
    """Small protocol surface the adapter needs from the YouTube client."""

    def search(self) -> _ListResource:
        """Return the search resource wrapper."""

    def videos(self) -> _ListResource:
        """Return the videos resource wrapper."""

    def channels(self) -> _ListResource:
        """Return the channels resource wrapper."""


def _items_from_response(response: Mapping[str, JSONValue]) -> list[JSONObject]:
    """Extract a list of object items from a YouTube API response payload."""
    items = response.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def search_videos(
    client: YouTubeClient,
    *,
    topic: str,
    max_items: int,
    published_after: str | None,
) -> list[JSONObject]:
    """Run the YouTube search.list call and return the raw item objects."""
    log(f"[srp] youtube: searching for {topic!r} (up to {max_items} results)")
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


def hydrate_videos(client: YouTubeClient, *, video_ids: list[str]) -> list[JSONObject]:
    """Hydrate video ids through videos.list and return the raw item objects."""
    log(f"[srp] youtube: fetching details for {len(video_ids)} video(s)")
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


def hydrate_channels(client: YouTubeClient, *, channel_ids: list[str]) -> list[JSONObject]:
    """Hydrate channel ids through channels.list and return the raw item objects."""
    log(f"[srp] youtube: fetching details for {len(channel_ids)} channel(s)")
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


@dataclass
class YoutubeQuery:
    """Input for YoutubeAPIFetch.execute()."""

    api_key: str
    topic: str
    max_items: int
    published_after: str | None = None


class YoutubeAPIFetch(BaseTechnology[YoutubeQuery, list]):
    """Technology adapter: fetch YouTube search results via the Data API v3."""

    name: ClassVar[str] = "youtube_api"
    health_check_key: ClassVar[str] = "youtube_api"
    enabled_config_key: ClassVar[str] = "youtube_api"

    async def _execute(self, data: YoutubeQuery) -> list:
        import asyncio

        client = build_client(data.api_key)
        raw = await asyncio.to_thread(
            search_videos,
            client,
            topic=data.topic,
            max_items=data.max_items,
            published_after=data.published_after,
        )
        return raw
