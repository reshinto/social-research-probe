"""Deterministic YouTube-shaped adapter for tests. Registered on import."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from social_research_probe.platforms.base import (
    FetchLimits,
    RawItem,
    SearchClient,
)
from social_research_probe.platforms.registry import register
from social_research_probe.utils.core.types import AdapterConfig


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
class FakeYouTubeClient(SearchClient):
    name: ClassVar[str] = "youtube"
    default_limits: ClassVar[FetchLimits] = FetchLimits()

    def __init__(self, config: AdapterConfig) -> None:
        self.config = config

    def health_check(self) -> bool:
        return True

    def find_by_topic(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        return _fixture_items(topic, n=min(5, limits.max_items))

    async def fetch_item_details(self, items: list[RawItem]) -> list[RawItem]:
        return items
