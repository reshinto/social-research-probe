"""google-api-python-client wrappers. Real calls; tests don't import this."""

from __future__ import annotations

from collections.abc import Mapping

from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.core.types import JSONObject, JSONValue
from social_research_probe.utils.display.progress import log_with_time

_ENV_KEY = "SRP_YOUTUBE_API_KEY"
_SECRET_KEY = "youtube_api_key"


def _build_client(api_key: str):
    """Build client for the next caller.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        api_key: Provider API key used for the current request.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _build_client(
                api_key="AIza-demo",
            )
        Output:
            "AI safety"
    """
    from googleapiclient.discovery import build

    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def _items_from_response(response: Mapping[str, JSONValue]) -> list[JSONObject]:
    """Document the items from response rule at the boundary where callers use it.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        response: Source text, prompt text, or raw value being parsed, normalized, classified, or
                  sent to a provider.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _items_from_response(
                response="42",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
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

    Fetch adapters hide provider response details and return the stable source-item shape used by
    services.

    Args:
        api_key: Provider API key used for the current request.
        topic: Research topic text or existing topic list used for classification and suggestions.
        max_items: Ordered source items being carried through the current pipeline step.
        published_after: Timestamp used for recency filtering, age calculations, or persisted audit
                         metadata.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Raises:
                    AdapterError: If the YouTube API request fails.



    Examples:
        Input:
            _search_videos(
                api_key="AIza-demo",
                topic="AI safety",
                max_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                published_after="2026-01-01T00:00:00Z",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
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

    Fetch adapters hide provider response details and return the stable source-item shape used by
    services.

    Args:
        api_key: Provider API key used for the current request.
        video_ids: YouTube video ids batched into a single metadata request.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Raises:
                    AdapterError: If the YouTube API request fails.



    Examples:
        Input:
            _fetch_video_details(
                api_key="AIza-demo",
                video_ids=["abc123", "def456"],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
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

    Fetch adapters hide provider response details and return the stable source-item shape used by
    services.

    Args:
        api_key: Provider API key used for the current request.
        channel_ids: YouTube channel name, id, or classification map used for source labeling.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Raises:
                    AdapterError: If the YouTube API request fails.



    Examples:
        Input:
            _fetch_channel_details(
                api_key="AIza-demo",
                channel_ids=["UC123", "UC456"],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
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

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Raises:
                    AdapterError: If no API key is available.



    Examples:
        Input:
            resolve_youtube_api_key()
        Output:
            "AI safety"
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
    """Return True when the YouTube API key can be resolved.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            youtube_health_check()
        Output:
            True
    """
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

    Fetch adapters hide provider response details and return the stable source-item shape used by
    services.

    Args:
        topic: Research topic text or existing topic list used for classification and suggestions.
        max_items: Ordered source items being carried through the current pipeline step.
        published_after: Timestamp used for recency filtering, age calculations, or persisted audit
                         metadata.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Raises:
                    AdapterError: If credentials are missing or the API request fails.



    Examples:
        Input:
            search_youtube(
                topic="AI safety",
                max_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                published_after="2026-01-01T00:00:00Z",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return _search_videos(
        resolve_youtube_api_key(),
        topic=topic,
        max_items=max_items,
        published_after=published_after,
    )


def _fetch_comment_threads(
    client,
    video_id: str,
    max_results: int,
    order: str,
) -> list[JSONObject]:
    """Fetch comment threads without exposing provider details to callers.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        client: Provider or runner selected for this operation.
        video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                  fetched.
        max_results: Count, database id, index, or limit that bounds the work being performed.
        order: Provider ordering mode, such as relevance or time.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _fetch_comment_threads(
                client=youtube_client,
                video_id="abc123",
                max_results=3,
                order="relevance",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    resp = (
        client.commentThreads()
        .list(
            videoId=video_id,
            part="snippet",
            maxResults=max_results,
            textFormat="plainText",
            order=order,
        )
        .execute()
    )
    items = resp.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


@log_with_time("[srp] youtube: comments {video_id!r}")
def fetch_youtube_comments(
    video_id: str,
    *,
    max_results: int = 20,
    order: str = "relevance",
) -> list[JSONObject]:
    """Fetch top-level comment threads for a YouTube video.

    Fetch adapters hide provider response details and return the stable source-item shape used by
    services.

    Args:
        video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                  fetched.
        max_results: Count, database id, index, or limit that bounds the work being performed.
        order: Provider ordering mode, such as relevance or time.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Raises:
                    AdapterError: If the API key is missing.
                    Exception: API errors propagate to the caller.



    Examples:
        Input:
            fetch_youtube_comments(
                video_id="abc123",
                max_results=3,
                order="relevance",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    api_key = resolve_youtube_api_key()
    client = _build_client(api_key)
    return _fetch_comment_threads(client, video_id, max_results, order)


@log_with_time("[srp] youtube: hydrate")
async def hydrate_youtube(
    video_ids: list[str],
    channel_ids: list[str],
) -> tuple[list[JSONObject], list[JSONObject]]:
    """Fetch YouTube video and channel details concurrently.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        video_ids: YouTube video ids batched into a single metadata request.
        channel_ids: YouTube channel name, id, or classification map used for source labeling.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Raises:
                        AdapterError: If credentials are missing or either API request fails.




    Examples:
        Input:
            await hydrate_youtube(
                video_ids=["abc123", "def456"],
                channel_ids=["UC123", "UC456"],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    import asyncio

    api_key = resolve_youtube_api_key()
    videos, channels = await asyncio.gather(
        asyncio.to_thread(_fetch_video_details, api_key, video_ids=video_ids),
        asyncio.to_thread(_fetch_channel_details, api_key, channel_ids=channel_ids),
    )
    return videos, channels
