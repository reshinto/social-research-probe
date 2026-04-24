"""Real YouTubeAdapter. In tests, `tests/fixtures/fake_youtube.py` pre-empts
this registration. In production, this module is imported and replaces the
fixture's registration."""

from __future__ import annotations

import asyncio
import os
import re
from datetime import UTC
from typing import ClassVar

from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import register
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.core.types import AdapterConfig, JSONObject


def _coerce_object(value: object) -> JSONObject:
    """Return value when it is a dict-like object, otherwise an empty object."""
    return value if isinstance(value, dict) else {}


def _coerce_string(value: object) -> str:
    """Return value when it is already a string, otherwise an empty string."""
    return value if isinstance(value, str) else ""


def _as_optional_string(value: object) -> str | None:
    """Return value when it is a non-empty string, otherwise None."""
    return value if isinstance(value, str) and value else None


def _coerce_int(value: object) -> int:
    """Coerce integer-like values from the API payload into plain ints."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


@register
class YouTubeAdapter(PlatformAdapter):
    name: ClassVar[str] = "youtube"
    default_limits: ClassVar[FetchLimits] = FetchLimits(max_items=50, recency_days=90)

    def __init__(self, config: AdapterConfig) -> None:
        """Store the merged config built from config.toml and CLI overrides."""
        self.config = config

    def _client(self) -> object:
        """Build a fresh Google API client per call.

        A previous implementation cached the client across ``search`` and
        ``enrich`` for a ~300ms cold-start saving, but httplib2's keep-alive
        socket could go stale in the gap between calls and surface as an SSL
        record-layer failure. Rebuilding is cheap enough and fully robust.
        """
        from social_research_probe.technologies.media_fetch import youtube_api as fetch

        return fetch.build_client(self._api_key())

    def _api_key(self) -> str:
        """Resolve the YouTube API key from env first, then the secrets file."""
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
        """Return True when the adapter can resolve a usable API key."""
        self._api_key()
        return True

    @staticmethod
    def _parse_duration_seconds(duration: str) -> int:
        """Parse an ISO 8601 YouTube duration string into seconds."""
        m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if not m:
            return 0
        h, mn, s = (int(v or 0) for v in m.groups())
        return h * 3600 + mn * 60 + s

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        """Search YouTube videos for a topic and normalise the result set."""
        from datetime import datetime, timedelta

        from social_research_probe.technologies.media_fetch import youtube_api as fetch

        client = self._client()
        published_after = None
        if limits.recency_days:
            dt = datetime.now(UTC) - timedelta(days=limits.recency_days)
            published_after = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        raw = fetch.search_videos(
            client, topic=topic, max_items=limits.max_items, published_after=published_after
        )
        return self._items_from_search(raw)

    def _items_from_search(self, raw: list[JSONObject]) -> list[RawItem]:
        """Convert raw search payload objects into the project's RawItem shape."""
        from datetime import datetime

        items: list[RawItem] = []
        for r in raw:
            id_block = _coerce_object(r.get("id"))
            vid_id = _coerce_string(id_block.get("videoId"))
            sn = _coerce_object(r.get("snippet"))
            published_raw = _coerce_string(sn.get("publishedAt"))
            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                ).astimezone(UTC)
            except ValueError:
                published_at = datetime.now(UTC)
            thumbnails = _coerce_object(sn.get("thumbnails"))
            default_thumb = _coerce_object(thumbnails.get("default"))
            thumb = _as_optional_string(default_thumb.get("url"))
            items.append(
                RawItem(
                    id=vid_id,
                    url=f"https://www.youtube.com/watch?v={vid_id}",
                    title=_coerce_string(sn.get("title")),
                    author_id=_coerce_string(sn.get("channelId")),
                    author_name=_coerce_string(sn.get("channelTitle")),
                    published_at=published_at,
                    metrics={},
                    text_excerpt=_as_optional_string(sn.get("description")),
                    thumbnail=thumb,
                    extras={},
                )
            )
        return items

    async def enrich(self, items: list[RawItem]) -> list[RawItem]:
        """Hydrate search results with video and channel statistics.

        ``hydrate_videos`` and ``hydrate_channels`` are independent API calls
        that share the same client but touch different YouTube endpoints. They
        run concurrently via asyncio.gather to halve the network round-trip.
        """
        if not items:
            return items
        from social_research_probe.technologies.media_fetch import youtube_api as fetch

        client = self._client()
        video_ids = [it.id for it in items]
        channel_ids = list({it.author_id for it in items if it.author_id})

        async def _fetch_both() -> tuple[list, list]:
            videos_task = asyncio.to_thread(fetch.hydrate_videos, client, video_ids=video_ids)
            channels_task = asyncio.to_thread(
                fetch.hydrate_channels, client, channel_ids=channel_ids
            )
            return await asyncio.gather(videos_task, channels_task)

        raw_videos, raw_channels = await _fetch_both()
        hydrated = {str(v["id"]): v for v in raw_videos}
        channels = {str(c["id"]): c for c in raw_channels}
        enriched: list[RawItem] = []
        for it in items:
            vid = hydrated.get(it.id, {})
            stats = _coerce_object(vid.get("statistics"))
            ch = channels.get(it.author_id, {})
            ch_stats = _coerce_object(ch.get("statistics"))
            metrics = {
                "views": _coerce_int(stats.get("viewCount")),
                "likes": _coerce_int(stats.get("likeCount")),
                "comments": _coerce_int(stats.get("commentCount")),
            }
            extras = {
                "channel_subscribers": _coerce_int(ch_stats.get("subscriberCount")),
                "channel_video_count": _coerce_int(ch_stats.get("videoCount")),
            }
            content_details = _coerce_object(vid.get("contentDetails"))
            duration_str = _coerce_string(content_details.get("duration"))
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
        """Derive scoring signals directly from enriched item metrics."""
        from datetime import datetime

        now = datetime.now(UTC)
        signals: list[SignalSet] = []
        for it in items:
            age_days = max(1, (now - it.published_at).days)
            views = _coerce_int(it.metrics.get("views"))
            likes = _coerce_int(it.metrics.get("likes"))
            comments = _coerce_int(it.metrics.get("comments"))
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
        """Extract trust metadata from the enriched channel fields."""
        return TrustHints(
            account_age_days=None,
            verified=None,
            subscriber_count=_coerce_int(item.extras.get("channel_subscribers")) or None,
            upload_cadence_days=None,
            citation_markers=[],
        )

    def url_normalize(self, url: str) -> str:
        """Normalise a YouTube URL down to its canonical watch id."""
        from urllib.parse import parse_qs, urlparse, urlunparse

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        keep = {"v": qs["v"]} if "v" in qs else {}
        query = "&".join(f"{k}={v[0]}" for k, v in keep.items())
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))
