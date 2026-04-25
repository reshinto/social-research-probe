"""YouTubeConnector: SearchClient implementation for YouTube sourcing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.platforms.base import (
    FetchLimits,
    RawItem,
    SearchClient,
    EngagementMetrics,
)

from social_research_probe.platforms.registry import register
from social_research_probe.technologies.media_fetch.youtube_api import (
    hydrate_youtube,
    search_youtube,
    youtube_health_check,
)
from social_research_probe.utils.core.coerce import (
    as_optional_string,
    coerce_int,
    coerce_object,
    coerce_string,
    parse_duration_seconds,
)
from social_research_probe.utils.core.types import AdapterConfig, JSONObject


def _recency_cutoff(days: int | None) -> str | None:
    if not days:
        return None
    dt = datetime.now(UTC) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@register
class YouTubeConnector(SearchClient):
    """Bridges the YouTubeAPI technology to the platform pipeline protocol."""

    name: ClassVar[str] = "youtube"

    def __init__(self, config: AdapterConfig) -> None:
        self.config = config
        platform = load_active_config().platform_defaults("youtube")
        self.default_limits = FetchLimits(
            max_items=int(platform.get("max_items", FetchLimits().max_items)),
            recency_days=platform.get("recency_days", FetchLimits().recency_days),
        )

    def health_check(self) -> bool:
        return youtube_health_check()

    def find_by_topic(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        raw = search_youtube(
            topic,
            max_items=limits.max_items,
            published_after=_recency_cutoff(limits.recency_days),
        )
        return self._parse_search_results(raw)

    async def fetch_item_details(self, items: list[RawItem]) -> list[RawItem]:
        if not items:
            return items
        raw_videos, raw_channels = await self._fetch_raw_api_data(items)
        hydrated = {str(v["id"]): v for v in raw_videos}
        channels = {str(c["id"]): c for c in raw_channels}
        enriched = [
            self._merge_video_and_channel_data(it, hydrated.get(it.id, {}), channels.get(it.author_id, {}))
            for it in items
        ]
        return self._filter_shorts(enriched)

    async def _fetch_raw_api_data(self, items: list[RawItem]):
        video_ids = [it.id for it in items]
        channel_ids = list({it.author_id for it in items if it.author_id})
        return await hydrate_youtube(video_ids, channel_ids)

    def _filter_shorts(self, items: list[RawItem]) -> list[RawItem]:
        if self.config.get("include_shorts", True):
            return items
        return [it for it in items if not it.extras.get("is_short")]

    def _parse_search_results(self, raw: list[JSONObject]) -> list[RawItem]:
        items: list[RawItem] = []
        for r in raw:
            id_block = coerce_object(r.get("id"))
            vid_id = coerce_string(id_block.get("videoId"))
            sn = coerce_object(r.get("snippet"))
            published_raw = coerce_string(sn.get("publishedAt"))
            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                ).astimezone(UTC)
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

    def _merge_video_and_channel_data(self, item: RawItem, vid: JSONObject, ch: JSONObject) -> RawItem:
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


def compute_engagement_metrics(items: list[RawItem]) -> list[EngagementMetrics]:
    """Compute engagement engagement_metrics from raw item metrics. Pure calculation, no I/O."""
    now = datetime.now(UTC)
    engagement_metrics: list[EngagementMetrics] = []
    for it in items:
        age_days = max(1, (now - it.published_at).days)
        views = coerce_int(it.metrics.get("views"))
        likes = coerce_int(it.metrics.get("likes"))
        comments = coerce_int(it.metrics.get("comments"))
        engagement_metrics.append(
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
    return engagement_metrics
