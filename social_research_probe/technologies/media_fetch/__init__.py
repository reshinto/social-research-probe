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
    SourceComment,
)


def _recency_cutoff(days: int | None) -> str | None:
    """Calculate the oldest publish date allowed by the fetch limits.

    Fetch adapters hide provider response details and return the stable source-item shape used by
    services.

    Args:
        days: Number of recency days used to compute the provider cutoff.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _recency_cutoff(
                days="AI safety",
            )
        Output:
            "AI safety"
    """
    if not days:
        return None
    dt = datetime.now(UTC) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_search_results(raw: list[JSONObject]) -> list[RawItem]:
    """Parse search results into the project format.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        raw: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to
             a provider.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _parse_search_results(
                raw="42",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Return an item with the comment fields expected by later enrichment and reports.

    Fetch adapters hide provider response details and return the stable source-item shape used by
    services.

    Args:
        item: Single source item, database row, or registry entry being transformed.
        vid: Video metadata record from the provider response.
        ch: Channel metadata record from the provider response.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _merge_video_and_channel_data(
                item={"title": "Example", "url": "https://youtu.be/demo"},
                vid="AI safety",
                ch="AI safety",
            )
        Output:
            "AI safety"
    """
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
    """Filter shorts before items enter ranking or reporting.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        include_shorts: Flag that selects the branch for this operation.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _filter_shorts(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                include_shorts=True,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    if include_shorts:
        return items
    return [it for it in items if not it.extras.get("is_short")]


class YouTubeSearchTech(BaseTechnology[tuple[str, FetchLimits], list[RawItem]]):
    """Search YouTube by topic and parse the raw API response into RawItems.

    Examples:
        Input:
            YouTubeSearchTech
        Output:
            YouTubeSearchTech
    """

    name: ClassVar[str] = "youtube_search"
    enabled_config_key: ClassVar[str] = "youtube_search"

    async def _execute(self, data: tuple[str, FetchLimits]) -> list[RawItem]:
        """Run this component and return the project-shaped output expected by its service.

        Fetch adapters hide provider response details and give services the stable source-item shape the
        rest of the project expects.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
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
    """Hydrate RawItems with video + channel statistics; optionally filter shorts.

    Examples:
        Input:
            YouTubeHydrateTech
        Output:
            YouTubeHydrateTech
    """

    name: ClassVar[str] = "youtube_hydrate"
    enabled_config_key: ClassVar[str] = "youtube_hydrate"

    async def _execute(self, data: tuple[list[RawItem], bool]) -> list[RawItem]:
        """Build the small payload that carries id through this workflow.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
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
    """Compute engagement metrics from hydrated items. Pure calculation.

    Examples:
        Input:
            YouTubeEngagementTech
        Output:
            YouTubeEngagementTech
    """

    name: ClassVar[str] = "youtube_engagement"
    enabled_config_key: ClassVar[str] = "youtube_engagement"

    async def _execute(self, items: list[RawItem]) -> list[EngagementMetrics]:
        """Run this component and return the project-shaped output expected by its service.

        Fetch adapters hide provider response details and give services the stable source-item shape the
        rest of the project expects.

        Args:
            items: Ordered source items being carried through the current pipeline step.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
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


def _parse_comment_thread(item: JSONObject, video_id: str) -> SourceComment | None:
    """Extract a SourceComment from a raw commentThreads.list item.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        item: Single source item, database row, or registry entry being transformed.
        video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                  fetched.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _parse_comment_thread(
                item={"title": "Example", "url": "https://youtu.be/demo"},
                video_id="abc123",
            )
        Output:
            "AI safety"
    """
    snippet = item.get("snippet")
    if not isinstance(snippet, dict):
        return None
    top = snippet.get("topLevelComment")
    if not isinstance(top, dict):
        return None
    top_snippet = top.get("snippet")
    if not isinstance(top_snippet, dict):
        return None
    comment_id = top.get("id")
    if not comment_id:
        return None
    return SourceComment(
        source_id=video_id,
        platform="youtube",
        comment_id=str(comment_id),
        author=str(top_snippet.get("authorDisplayName") or ""),
        text=str(top_snippet.get("textDisplay") or ""),
        like_count=int(top_snippet.get("likeCount") or 0),
        published_at=str(top_snippet.get("publishedAt") or ""),
    )


class YouTubeCommentsTech(BaseTechnology[tuple[str, int, str], list[SourceComment]]):
    """Fetch and parse YouTube top-level comments for a video.

    Examples:
        Input:
            YouTubeCommentsTech
        Output:
            YouTubeCommentsTech
    """

    name: ClassVar[str] = "youtube_comments"
    enabled_config_key: ClassVar[str] = "youtube_comments"

    async def _execute(self, data: tuple[str, int, str]) -> list[SourceComment]:
        """Run this component and return the project-shaped output expected by its service.

        Fetch adapters hide provider response details and give services the stable source-item shape the
        rest of the project expects.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        from social_research_probe.technologies.media_fetch.youtube_api import (
            fetch_youtube_comments,
        )

        video_id, max_results, order = data
        raw = await asyncio.to_thread(
            fetch_youtube_comments, video_id, max_results=max_results, order=order
        )
        result: list[SourceComment] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            parsed = _parse_comment_thread(item, video_id)
            if parsed is not None:
                result.append(parsed)
        return result
