"""Real YouTubeAdapter. In tests, `tests/fixtures/fake_youtube.py` pre-empts
this registration. In production, this module is imported and replaces the
fixture's registration."""

from __future__ import annotations

import os
import re
from datetime import UTC
from typing import Any, ClassVar

from social_research_probe.errors import AdapterError
from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import register


@register
class YouTubeAdapter(PlatformAdapter):
    name: ClassVar[str] = "youtube"
    default_limits: ClassVar[FetchLimits] = FetchLimits(max_items=20, recency_days=90)

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _api_key(self) -> str:
        key = os.environ.get("SRP_YOUTUBE_API_KEY")
        if key:
            return key
        data_dir = self.config.get("data_dir")
        if data_dir is not None:
            from social_research_probe.commands.config import read_secret

            val = read_secret(data_dir, "youtube_api_key")
            if val:
                return val
        raise AdapterError(
            "youtube_api_key missing — run `srp config set-secret youtube_api_key` in a terminal"
        )

    def health_check(self) -> bool:
        self._api_key()
        return True

    @staticmethod
    def _parse_duration_seconds(duration: str) -> int:
        m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if not m:
            return 0
        h, mn, s = (int(v or 0) for v in m.groups())
        return h * 3600 + mn * 60 + s

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        from datetime import datetime, timedelta

        from social_research_probe.platforms.youtube import fetch

        client = fetch.build_client(self._api_key())
        published_after = None
        if limits.recency_days:
            dt = datetime.now(UTC) - timedelta(days=limits.recency_days)
            published_after = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        raw = fetch.search_videos(
            client, topic=topic, max_items=limits.max_items, published_after=published_after
        )
        return self._items_from_search(raw)

    def _items_from_search(self, raw: list[dict]) -> list[RawItem]:
        from datetime import datetime

        items = []
        for r in raw:
            vid_id = r.get("id", {}).get("videoId", "")
            sn = r.get("snippet", {})
            published_raw = sn.get("publishedAt", "")
            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                ).astimezone(UTC)
            except ValueError:
                published_at = datetime.now(UTC)
            thumb = (sn.get("thumbnails") or {}).get("default", {}).get("url")
            items.append(
                RawItem(
                    id=vid_id,
                    url=f"https://www.youtube.com/watch?v={vid_id}",
                    title=sn.get("title", ""),
                    author_id=sn.get("channelId", ""),
                    author_name=sn.get("channelTitle", ""),
                    published_at=published_at,
                    metrics={},
                    text_excerpt=sn.get("description") or None,
                    thumbnail=thumb,
                    extras={},
                )
            )
        return items

    def enrich(self, items: list[RawItem]) -> list[RawItem]:
        if not items:
            return items
        from social_research_probe.platforms.youtube import fetch

        client = fetch.build_client(self._api_key())
        video_ids = [it.id for it in items]
        hydrated = {v["id"]: v for v in fetch.hydrate_videos(client, video_ids=video_ids)}
        channel_ids = list({it.author_id for it in items if it.author_id})
        channels = {c["id"]: c for c in fetch.hydrate_channels(client, channel_ids=channel_ids)}
        enriched = []
        for it in items:
            vid = hydrated.get(it.id, {})
            stats = vid.get("statistics", {})
            ch = channels.get(it.author_id, {})
            ch_stats = ch.get("statistics", {})
            metrics = {
                "views": int(stats.get("viewCount", 0) or 0),
                "likes": int(stats.get("likeCount", 0) or 0),
                "comments": int(stats.get("commentCount", 0) or 0),
            }
            extras = {
                "channel_subscribers": int(ch_stats.get("subscriberCount", 0) or 0),
                "channel_video_count": int(ch_stats.get("videoCount", 0) or 0),
            }
            duration_str = vid.get("contentDetails", {}).get("duration", "")
            secs = self._parse_duration_seconds(duration_str) if duration_str else 0
            is_short = 0 < secs < 90
            if is_short and not self.config.get("include_shorts", True):
                continue
            enriched.append(
                RawItem(
                    id=it.id,
                    url=it.url,
                    title=it.title,
                    author_id=it.author_id,
                    author_name=it.author_name,
                    published_at=it.published_at,
                    metrics=metrics,
                    text_excerpt=it.text_excerpt,
                    thumbnail=it.thumbnail,
                    extras={
                        **extras,
                        "duration_seconds": secs,
                        "is_short": is_short,
                    },
                )
            )
        return enriched

    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:
        from datetime import datetime

        now = datetime.now(UTC)
        signals = []
        for it in items:
            age_days = max(1, (now - it.published_at).days)
            views = it.metrics.get("views", 0) or 0
            likes = it.metrics.get("likes", 0) or 0
            comments = it.metrics.get("comments", 0) or 0
            signals.append(
                SignalSet(
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
        return signals

    def trust_hints(self, item: RawItem) -> TrustHints:
        return TrustHints(
            account_age_days=None,
            verified=None,
            subscriber_count=item.extras.get("channel_subscribers"),
            upload_cadence_days=None,
            citation_markers=[],
        )

    def url_normalize(self, url: str) -> str:
        from urllib.parse import parse_qs, urlparse, urlunparse

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        keep = {"v": qs["v"]} if "v" in qs else {}
        query = "&".join(f"{k}={v[0]}" for k, v in keep.items())
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))
