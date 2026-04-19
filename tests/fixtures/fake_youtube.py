"""Deterministic YouTube-shaped adapter for tests. Registered on import."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import register


def _fixture_items(topic: str, n: int = 5) -> list[RawItem]:
    now = datetime.now(UTC)
    items = []
    for i in range(n):
        items.append(
            RawItem(
                id=f"fake-{topic}-{i}",
                url=f"https://youtube.com/watch?v=fake{i}",
                title=f"{topic} — episode {i}",
                author_id=f"channel-{i % 3}",
                author_name=f"Channel {i % 3}",
                published_at=now - timedelta(days=i * 3),
                metrics={
                    "views": 10_000 * (i + 1),
                    "likes": 500 * (i + 1),
                    "comments": 50 * (i + 1),
                },
                text_excerpt=f"A video about {topic}. Content {i}.",
                thumbnail=f"https://img/{i}.jpg",
                extras={"channel_subscribers": 50_000 + i * 1000},
            )
        )
    return items


@register
class FakeYouTubeAdapter(PlatformAdapter):
    name: ClassVar[str] = "youtube"
    default_limits: ClassVar[FetchLimits] = FetchLimits()

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def health_check(self) -> bool:
        return True

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        return _fixture_items(topic, n=min(5, limits.max_items))

    def enrich(self, items: list[RawItem]) -> list[RawItem]:
        return items

    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:
        now = datetime.now(UTC)
        signals = []
        for item in items:
            age_days = max(1, (now - item.published_at).days)
            views = item.metrics.get("views", 0)
            likes = item.metrics.get("likes", 0)
            comments = item.metrics.get("comments", 0)
            signals.append(
                SignalSet(
                    views=views,
                    likes=likes,
                    comments=comments,
                    upload_date=item.published_at,
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
            account_age_days=1200,
            verified=True,
            subscriber_count=int(item.extras.get("channel_subscribers", 0)),
            upload_cadence_days=7.0,
            citation_markers=[],
        )

    def url_normalize(self, url: str) -> str:
        return url.split("&")[0]

    def fetch_text_for_claim_extraction(self, item: RawItem) -> str | None:
        return item.text_excerpt
