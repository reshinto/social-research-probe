"""Tests for services.sourcing.youtube (techs + service)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from social_research_probe.platforms.base import FetchLimits, RawItem
from social_research_probe.services.sourcing.youtube import (
    YouTubeEngagementTech,
    YouTubeHydrateTech,
    YouTubeSearchTech,
    YouTubeSourcingService,
    _filter_shorts,
    _parse_search_results,
    _recency_cutoff,
    run_youtube_sourcing,
)


def test_recency_cutoff_none():
    assert _recency_cutoff(None) is None
    assert _recency_cutoff(0) is None


def test_recency_cutoff_format():
    out = _recency_cutoff(7)
    assert out and "T" in out and out.endswith("Z")


def test_parse_search_results_basic():
    raw = [
        {
            "id": {"videoId": "vid1"},
            "snippet": {
                "publishedAt": "2025-01-01T00:00:00Z",
                "title": "T1",
                "channelId": "c1",
                "channelTitle": "Chan",
                "description": "d",
                "thumbnails": {"default": {"url": "https://thumb"}},
            },
        }
    ]
    items = _parse_search_results(raw)
    assert len(items) == 1
    assert items[0].url == "https://www.youtube.com/watch?v=vid1"
    assert items[0].title == "T1"


def test_parse_search_results_invalid_date():
    raw = [{"id": {"videoId": "v"}, "snippet": {"publishedAt": "garbage"}}]
    items = _parse_search_results(raw)
    assert items[0].id == "v"


def _short_item() -> RawItem:
    return RawItem(
        id="1",
        url="",
        title="",
        author_id="",
        author_name="",
        published_at=datetime.now(UTC),
        metrics={},
        text_excerpt=None,
        thumbnail=None,
        extras={"is_short": True},
    )


def test_filter_shorts_kept_when_enabled():
    assert len(_filter_shorts([_short_item()], True)) == 1


def test_filter_shorts_dropped_when_disabled():
    assert _filter_shorts([_short_item()], False) == []


def test_engagement_tech_empty():
    out = asyncio.run(YouTubeEngagementTech()._execute([]))
    assert out == []


def test_engagement_tech_basic():
    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="a",
        author_name="A",
        published_at=datetime.now(UTC) - timedelta(days=10),
        metrics={"views": 1000, "likes": 50, "comments": 10},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    out = asyncio.run(YouTubeEngagementTech()._execute([item]))
    assert len(out) == 1
    assert out[0].views == 1000
    assert out[0].view_velocity == 100.0
    assert out[0].engagement_ratio == 60 / 1000


def test_search_tech_calls_search_youtube(monkeypatch):
    captured = {}

    def fake_search(topic, *, max_items, published_after):
        captured["args"] = (topic, max_items, published_after)
        return [
            {
                "id": {"videoId": "v"},
                "snippet": {
                    "publishedAt": "2025-01-01T00:00:00Z",
                    "title": "T",
                    "channelId": "c",
                    "channelTitle": "Chan",
                },
            }
        ]

    monkeypatch.setattr(
        "social_research_probe.services.sourcing.youtube.search_youtube", fake_search
    )
    out = asyncio.run(YouTubeSearchTech()._execute(("topic", FetchLimits(max_items=3))))
    assert out[0].title == "T"
    assert captured["args"][0] == "topic"
    assert captured["args"][1] == 3


def test_hydrate_tech_empty():
    assert asyncio.run(YouTubeHydrateTech()._execute(([], True))) == []


def test_hydrate_tech_merges(monkeypatch):
    async def fake_hydrate(vids, chids):
        return [
            {
                "id": "1",
                "statistics": {"viewCount": "100"},
                "contentDetails": {"duration": "PT2M"},
            }
        ], [
            {
                "id": "ch",
                "statistics": {"subscriberCount": "5"},
                "snippet": {"publishedAt": "2024-01-01T00:00:00Z"},
            }
        ]

    monkeypatch.setattr(
        "social_research_probe.services.sourcing.youtube.hydrate_youtube", fake_hydrate
    )
    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="ch",
        author_name="C",
        published_at=datetime.now(UTC),
        metrics={},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    out = asyncio.run(YouTubeHydrateTech()._execute(([item], True)))
    assert out[0].metrics["views"] == 100
    assert out[0].extras["channel_subscribers"] == 5


def test_service_returns_three_techs():
    service = YouTubeSourcingService({"include_shorts": False})
    assert service.config.get("include_shorts") is False
    assert len(service._get_technologies()) == 3


def test_service_execute_one_chains_techs(monkeypatch):
    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="a",
        author_name="A",
        published_at=datetime.now(UTC) - timedelta(days=2),
        metrics={"views": 100, "likes": 1, "comments": 1},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )

    async def fake_search(_data):
        return [item]

    async def fake_hydrate(_data):
        return [item]

    cfg = MagicMock()
    cfg.platform_defaults.return_value = {"max_items": 5, "recency_days": 30}

    service = YouTubeSourcingService()
    monkeypatch.setattr(service._search, "execute", fake_search)
    monkeypatch.setattr(service._hydrate, "execute", fake_hydrate)
    with patch(
        "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
    ):
        result = asyncio.run(service.execute_one("topic"))

    assert result.service_name == "youtube.sourcing"
    assert [tr.tech_name for tr in result.tech_results] == [
        "youtube_search",
        "youtube_hydrate",
        "youtube_engagement",
    ]
    assert all(tr.success for tr in result.tech_results)


def test_service_execute_one_handles_search_failure(monkeypatch):
    cfg = MagicMock()
    cfg.platform_defaults.return_value = {"max_items": 5, "recency_days": 30}

    async def search_returns_none(_data):
        return None

    service = YouTubeSourcingService()
    monkeypatch.setattr(service._search, "execute", search_returns_none)
    with patch(
        "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
    ):
        result = asyncio.run(service.execute_one("topic"))
    names = [tr.tech_name for tr in result.tech_results]
    assert names == ["youtube_search", "youtube_hydrate", "youtube_engagement"]
    assert result.tech_results[0].success is False


def test_service_execute_one_handles_hydrate_failure(monkeypatch):
    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="a",
        author_name="A",
        published_at=datetime.now(UTC) - timedelta(days=1),
        metrics={"views": 1, "likes": 0, "comments": 0},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    cfg = MagicMock()
    cfg.platform_defaults.return_value = {}

    async def fake_search(_data):
        return [item]

    async def hydrate_returns_none(_data):
        return None

    async def fake_engagement(items):
        return await YouTubeEngagementTech()._execute(items)

    service = YouTubeSourcingService()
    monkeypatch.setattr(service._search, "execute", fake_search)
    monkeypatch.setattr(service._hydrate, "execute", hydrate_returns_none)
    monkeypatch.setattr(service._engagement, "execute", fake_engagement)
    with patch(
        "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
    ):
        result = asyncio.run(service.execute_one("topic"))
    assert result.tech_results[1].success is False
    assert result.tech_results[2].success is True


def test_service_execute_one_handles_engagement_failure(monkeypatch):
    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="a",
        author_name="A",
        published_at=datetime.now(UTC) - timedelta(days=1),
        metrics={"views": 1, "likes": 0, "comments": 0},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    cfg = MagicMock()
    cfg.platform_defaults.return_value = {}

    async def fake_search(_data):
        return [item]

    async def fake_hydrate(_data):
        return [item]

    async def engagement_returns_none(_items):
        return None

    service = YouTubeSourcingService()
    monkeypatch.setattr(service._search, "execute", fake_search)
    monkeypatch.setattr(service._hydrate, "execute", fake_hydrate)
    monkeypatch.setattr(service._engagement, "execute", engagement_returns_none)
    with patch(
        "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
    ):
        result = asyncio.run(service.execute_one("topic"))
    assert result.tech_results[2].success is False


def test_run_tech_captures_exception(monkeypatch):
    service = YouTubeSourcingService()

    async def boom(_data):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(service._search, "execute", boom)
    sink: list = []
    out = asyncio.run(
        service._run_tech(service._search, ("t", _resolve_default_limits_stub()), sink)
    )
    assert out is None
    assert sink[0].success is False
    assert "kaboom" in (sink[0].error or "")


def _resolve_default_limits_stub():
    return FetchLimits(max_items=1, recency_days=1)


def test_run_youtube_sourcing_returns_items_and_engagement(monkeypatch):
    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="a",
        author_name="A",
        published_at=datetime.now(UTC) - timedelta(days=5),
        metrics={"views": 100, "likes": 1, "comments": 1},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    engagement = asyncio.run(YouTubeEngagementTech()._execute([item]))

    async def fake_execute(self, data):
        from social_research_probe.services import ServiceResult, TechResult

        return ServiceResult(
            service_name=self.service_name,
            input_key=data,
            tech_results=[
                TechResult("youtube_search", data, [item], True),
                TechResult("youtube_hydrate", [item], [item], True),
                TechResult("youtube_engagement", [item], engagement, True),
            ],
        )

    monkeypatch.setattr(YouTubeSourcingService, "execute_one", fake_execute)
    items, em = asyncio.run(run_youtube_sourcing("topic"))
    assert len(items) == 1
    assert len(em) == 1
