"""Web search technology adapters."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import ClassVar

from social_research_probe.platforms import EngagementMetrics, FetchLimits, RawItem
from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.core.coerce import coerce_int


class YouTubeSearchTech(BaseTechnology[tuple[str, FetchLimits], list[RawItem]]):
    """Search YouTube by topic and parse the raw API response into RawItems."""

    name: ClassVar[str] = "youtube_search"

    async def _execute(self, data: tuple[str, FetchLimits]) -> list[RawItem]:
        from social_research_probe.services.sourcing.youtube import search_youtube

        topic, limits = data
        raw = await asyncio.to_thread(
            search_youtube,
            topic,
            max_items=limits.max_items,
            order=limits.order,
        )
        return raw


class YouTubeHydrateTech(BaseTechnology[tuple[list[RawItem], bool], list[RawItem]]):
    """Hydrate RawItems with video + channel statistics; optionally filter shorts."""

    name: ClassVar[str] = "youtube_hydrate"

    async def _execute(self, data: tuple[list[RawItem], bool]) -> list[RawItem]:
        from social_research_probe.services.sourcing.youtube import (
            get_channel_stats,
            get_video_stats,
        )

        items, include_shorts = data
        if not items:
            return items
        video_ids = [it.id for it in items]
        channel_ids = list({it.author_id for it in items if it.author_id})
        video_stats = await asyncio.to_thread(get_video_stats, video_ids)
        channel_stats = await asyncio.to_thread(get_channel_stats, channel_ids)

        for item in items:
            item.stats = video_stats.get(item.id)
            if item.author_id:
                item.author_stats = channel_stats.get(item.author_id)

        if not include_shorts:
            items = [it for it in items if not (it.stats and it.stats.get("height") == 1080)]
        return items


class YouTubeEngagementTech(BaseTechnology[list[RawItem], list[EngagementMetrics]]):
    """Compute engagement metrics from hydrated items. Pure calculation."""

    name: ClassVar[str] = "youtube_engagement"

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
