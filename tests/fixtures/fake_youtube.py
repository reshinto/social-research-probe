"""Deterministic YouTube-shaped fixture data + service stub for tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from social_research_probe.platforms import EngagementMetrics, RawItem


def fixture_items(topic: str, n: int = 5) -> list[RawItem]:
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


def fixture_engagement(items: list[RawItem]) -> list[EngagementMetrics]:
    now = datetime.now(UTC)
    out = []
    for it in items:
        age_days = max(1, (now - it.published_at).days)
        views = int(it.metrics.get("views", 0) or 0)
        likes = int(it.metrics.get("likes", 0) or 0)
        comments = int(it.metrics.get("comments", 0) or 0)
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


async def fake_execute_one(self, topic: str):
    from social_research_probe.services import ServiceResult, TechResult
    from social_research_probe.technologies.media_fetch import (
        YouTubeEngagementTech,
        YouTubeHydrateTech,
        YouTubeSearchTech,
    )

    items = fixture_items(topic)
    engagement = fixture_engagement(items)
    return ServiceResult(
        service_name="youtube_sourcing",
        input_key=topic,
        tech_results=[
            TechResult(YouTubeSearchTech.name, topic, items, True),
            TechResult(YouTubeHydrateTech.name, items, items, True),
            TechResult(YouTubeEngagementTech.name, items, engagement, True),
        ],
    )
