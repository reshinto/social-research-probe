"""google-api-python-client wrappers. Real calls; tests don't import this."""

from __future__ import annotations

from typing import Any

from social_research_probe.errors import AdapterError


def build_client(api_key: str):
    from googleapiclient.discovery import build

    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def search_videos(
    client: Any, *, topic: str, max_items: int, published_after: str | None
) -> list[dict]:
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
    return resp.get("items", [])


def hydrate_videos(client: Any, *, video_ids: list[str]) -> list[dict]:
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
    return resp.get("items", [])


def hydrate_channels(client: Any, *, channel_ids: list[str]) -> list[dict]:
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
    return resp.get("items", [])
