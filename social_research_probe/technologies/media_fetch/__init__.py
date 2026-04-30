"""Media fetch technology adapters (YouTube API, yt-dlp)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.core.coerce import (
    as_optional_string,
    coerce_int,
    coerce_object,
    coerce_string,
    parse_duration_seconds,
)
from social_research_probe.utils.core.types import (
    EngagementMetrics,
    FetchLimits,
    JSONObject,
    RawItem,
)


def _recency_cutoff(days: int | None) -> str | None:
    if not days:
        return None
    dt = datetime.now(UTC) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_search_results(raw: list[JSONObject]) -> list[RawItem]:
    items: list[RawItem] = []
    for r in raw:
        id_block = coerce_object(r.get("id"))
        vid_id = coerce_string(id_block.get("videoId"))
        sn = coerce_object(r.get("snippet"))
        published_raw = coerce_string(sn.get("publishedAt"))
        try:
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).astimezone(
                UTC
            )
        except ValueError:
            published_at = datetime.now(UTC)
        thumbnails = coerce_object(sn.get("thumbnails"))
        thumb = as_optional_string(coerce_object(thumbnails.get("default")).get("url"))
        items.append(
            RawItem(
                id=vid_id,
                url=f"https://www.youtube.com/watch?v={vid_id}",
                title=coerce_string(sn.get("title")),
                author_id=coerce_string(sn.get("channelId")),
                author_name=coerce_string(sn.get("channelTitle")),
                published_at=published_at,
                metrics={},
                text_excerpt=as_optional_string(sn.get("description")),
                thumbnail=thumb,
                extras={},
            )
        )
    return items


def _merge_video_and_channel_data(item: RawItem, vid: JSONObject, ch: JSONObject) -> RawItem:
    stats = coerce_object(vid.get("statistics"))
    ch_stats = coerce_object(ch.get("statistics"))
    ch_snippet = coerce_object(ch.get("snippet"))
    duration_str = coerce_string(coerce_object(vid.get("contentDetails")).get("duration"))
    secs = parse_duration_seconds(duration_str) if duration_str else 0
    is_short = 0 < secs < 90
    return RawItem(
        id=item.id,
        url=item.url,
        title=item.title,
        author_id=item.author_id,
        author_name=item.author_name,
        published_at=item.published_at,
        metrics={
            "views": coerce_int(stats.get("viewCount")),
            "likes": coerce_int(stats.get("likeCount")),
            "comments": coerce_int(stats.get("commentCount")),
        },
        text_excerpt=item.text_excerpt,
        thumbnail=item.thumbnail,
        extras={
            "channel_subscribers": coerce_int(ch_stats.get("subscriberCount")),
            "channel_video_count": coerce_int(ch_stats.get("videoCount")),
            "channel_created_at": as_optional_string(ch_snippet.get("publishedAt")),
            "duration_seconds": secs,
            "is_short": is_short,
        },
    )


def _filter_shorts(items: list[RawItem], include_shorts: bool) -> list[RawItem]:
    if include_shorts:
        return items
    return [it for it in items if not it.extras.get("is_short")]


class YouTubeSearchTech(BaseTechnology[tuple[str, FetchLimits], list[RawItem]]):
    """Search YouTube by topic and parse the raw API response into RawItems."""

    name: ClassVar[str] = "youtube_search"
    enabled_config_key: ClassVar[str] = "youtube_search"

    async def _execute(self, data: tuple[str, FetchLimits]) -> list[RawItem]:
        from social_research_probe.technologies.media_fetch.youtube_api import (
            search_youtube,
        )

        topic, limits = data
        raw = await asyncio.to_thread(
            search_youtube,
            topic,
            max_items=limits.max_items,
            published_after=_recency_cutoff(limits.recency_days),
        )
        return _parse_search_results(raw)


class YouTubeHydrateTech(BaseTechnology[tuple[list[RawItem], bool], list[RawItem]]):
    """Hydrate RawItems with video + channel statistics; optionally filter shorts."""

    name: ClassVar[str] = "youtube_hydrate"
    enabled_config_key: ClassVar[str] = "youtube_hydrate"

    async def _execute(self, data: tuple[list[RawItem], bool]) -> list[RawItem]:
        from social_research_probe.technologies.media_fetch.youtube_api import (
            hydrate_youtube,
        )

        items, include_shorts = data
        if not items:
            return items
        video_ids = [it.id for it in items]
        channel_ids = list({it.author_id for it in items if it.author_id})
        raw_videos, raw_channels = await hydrate_youtube(video_ids, channel_ids)
        videos = {str(v["id"]): v for v in raw_videos}
        channels = {str(c["id"]): c for c in raw_channels}
        enriched = [
            _merge_video_and_channel_data(it, videos.get(it.id, {}), channels.get(it.author_id, {}))
            for it in items
        ]
        return _filter_shorts(enriched, include_shorts)


class YouTubeEngagementTech(BaseTechnology[list[RawItem], list[EngagementMetrics]]):
    """Compute engagement metrics from hydrated items. Pure calculation."""

    name: ClassVar[str] = "youtube_engagement"
    enabled_config_key: ClassVar[str] = "youtube_engagement"

    async def _execute(self, items: list[RawItem]) -> list[EngagementMetrics]:
        now = datetime.now(UTC)
        out: list[EngagementMetrics] = []
        for it in items:
            age_days = max(1, (now - it.published_at).days)
            views = coerce_int(it.metrics.get("views"))
            likes = coerce_int(it.metrics.get("likes"))
            comments = coerce_int(it.metrics.get("comments"))
            out.append(
                EngagementMetrics(
                    views=views,
                    likes=likes,
                    comments=comments,
                    upload_date=it.published_at,
                    view_velocity=views / age_days,
                    engagement_ratio=(likes + comments) / max(1, views),
                    comment_velocity=comments / age_days,
                    cross_channel_repetition=0.0,
                    raw={},
                )
            )
        return out
