"""Cover remaining gaps: yt_transcript_api, sourcing/youtube, charts service, statistics service, llm runner branches."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.platforms.base import RawItem
from social_research_probe.services.analyzing import charts as charts_svc
from social_research_probe.services.analyzing import statistics as stats_svc
from social_research_probe.services.sourcing.youtube import YouTubeConnector, _recency_cutoff
from social_research_probe.technologies.transcript_fetch import whisper as whisper_mod
from social_research_probe.technologies.transcript_fetch import (
    youtube_transcript_api as yt_api,
)


class TestYouTubeTranscriptApi:
    def test_fetch_transcript_no_api(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        monkeypatch.setattr(yt_api, "_API_AVAILABLE", False)
        assert yt_api.fetch_transcript("https://youtube.com/watch?v=abc") is None

    def test_fetch_transcript_no_video_id(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        monkeypatch.setattr(yt_api, "_API_AVAILABLE", True)
        assert yt_api.fetch_transcript("https://nope.com") is None

    def test_fetch_transcript_cached(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        monkeypatch.setattr(yt_api, "_API_AVAILABLE", True)
        monkeypatch.setattr(yt_api, "get_str", lambda c, k: "cached transcript")
        assert (
            yt_api.fetch_transcript("https://youtube.com/watch?v=abcDEF12345")
            == "cached transcript"
        )

    def test_fetch_transcript_api_success(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        monkeypatch.setattr(yt_api, "_API_AVAILABLE", True)
        monkeypatch.setattr(yt_api, "get_str", lambda c, k: None)
        monkeypatch.setattr(yt_api, "set_str", lambda *a, **kw: None)

        class Snip:
            def __init__(self, t):
                self.text = t

        fake_api = MagicMock()
        fake_api.return_value.fetch.return_value = [Snip("hello"), Snip(""), Snip("world")]
        monkeypatch.setattr(yt_api, "YouTubeTranscriptApi", fake_api)
        out = yt_api.fetch_transcript("https://youtube.com/watch?v=abcDEF12345")
        assert "hello" in out and "world" in out

    def test_fetch_transcript_api_empty(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        monkeypatch.setattr(yt_api, "_API_AVAILABLE", True)
        monkeypatch.setattr(yt_api, "get_str", lambda c, k: None)
        fake_api = MagicMock()
        fake_api.return_value.fetch.return_value = []
        monkeypatch.setattr(yt_api, "YouTubeTranscriptApi", fake_api)
        assert yt_api.fetch_transcript("https://youtube.com/watch?v=abcDEF12345") is None

    def test_fetch_transcript_api_exception(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        monkeypatch.setattr(yt_api, "_API_AVAILABLE", True)
        monkeypatch.setattr(yt_api, "get_str", lambda c, k: None)
        fake_api = MagicMock()
        fake_api.return_value.fetch.side_effect = RuntimeError("net")
        monkeypatch.setattr(yt_api, "YouTubeTranscriptApi", fake_api)
        assert yt_api.fetch_transcript("https://youtube.com/watch?v=abcDEF12345") is None

    def test_get_transcript_uses_url(self, monkeypatch):
        captured = []
        monkeypatch.setattr(yt_api, "fetch_transcript", lambda url: captured.append(url) or "ok")
        out = yt_api.get_transcript("vidid")
        assert out == "ok" and "vidid" in captured[0]

    def test_execute_failure(self, monkeypatch):
        monkeypatch.setattr(yt_api, "fetch_transcript", lambda url: None)
        with pytest.raises(RuntimeError):
            asyncio.run(yt_api.YoutubeTranscriptFetch()._execute("u"))

    def test_execute_success(self, monkeypatch):
        monkeypatch.setattr(yt_api, "fetch_transcript", lambda url: "tx")
        assert asyncio.run(yt_api.YoutubeTranscriptFetch()._execute("u")) == "tx"


class TestWhisper:
    def test_transcribe_audio_no_module(self, monkeypatch, tmp_path):
        # Force ImportError
        monkeypatch.setitem(__import__("sys").modules, "whisper", None)
        result = whisper_mod.transcribe_audio(tmp_path / "x.mp3")
        assert result is None

    def test_transcribe_audio_success(self, monkeypatch, tmp_path):
        whisper_mod._MODEL_CACHE.clear()
        fake_model = MagicMock()
        fake_model.transcribe.return_value = {"text": "  hello  "}
        fake_module = MagicMock()
        fake_module.load_model.return_value = fake_model
        monkeypatch.setitem(__import__("sys").modules, "whisper", fake_module)
        out = whisper_mod.transcribe_audio(tmp_path / "x.mp3")
        assert out == "hello"


class TestSourcingYouTube:
    def test_recency_cutoff_zero(self):
        assert _recency_cutoff(0) is None

    def test_init_uses_config(self, monkeypatch):
        cfg = MagicMock()
        cfg.platform_defaults.return_value = {"max_items": 7, "recency_days": 14}
        with patch(
            "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
        ):
            conn = YouTubeConnector({})
        assert conn.default_limits.max_items == 7

    def test_health_check(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.sourcing.youtube.youtube_health_check",
            lambda: True,
        )
        cfg = MagicMock()
        cfg.platform_defaults.return_value = {}
        with patch(
            "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
        ):
            conn = YouTubeConnector({})
        assert conn.health_check() is True

    def test_find_by_topic(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.sourcing.youtube.search_youtube",
            lambda topic, max_items, published_after: [
                {
                    "id": {"videoId": "v"},
                    "snippet": {
                        "publishedAt": "2025-01-01T00:00:00Z",
                        "title": "T",
                        "channelId": "c",
                        "channelTitle": "Chan",
                    },
                }
            ],
        )
        cfg = MagicMock()
        cfg.platform_defaults.return_value = {}
        with patch(
            "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
        ):
            conn = YouTubeConnector({})
            from social_research_probe.platforms.base import FetchLimits

            out = conn.find_by_topic("t", FetchLimits())
        assert out[0].title == "T"

    def test_fetch_item_details_empty(self):
        cfg = MagicMock()
        cfg.platform_defaults.return_value = {}
        with patch(
            "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
        ):
            conn = YouTubeConnector({})
        assert asyncio.run(conn.fetch_item_details([])) == []

    def test_fetch_item_details_basic(self, monkeypatch):
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
        cfg = MagicMock()
        cfg.platform_defaults.return_value = {}
        with patch(
            "social_research_probe.services.sourcing.youtube.load_active_config", return_value=cfg
        ):
            conn = YouTubeConnector({})
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
        out = asyncio.run(conn.fetch_item_details([item]))
        assert out[0].metrics["views"] == 100
        assert out[0].extras["channel_subscribers"] == 5


class TestChartsService:
    def test_charts_cache(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        cache = charts_svc.ChartsService._charts_cache()
        assert cache is not None

    def test_render_with_cache_empty(self, tmp_path):
        out = asyncio.run(charts_svc.ChartsService._render_with_cache([], tmp_path))
        assert out == []

    def test_render_with_cache_hits(self, monkeypatch, tmp_path):
        png = tmp_path / "x.png"
        png.write_bytes(b"x")
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.get_json",
            lambda c, k: {"filenames": ["x.png"], "captions": ["cap"]},
        )
        out = asyncio.run(charts_svc.ChartsService._render_with_cache([{"id": "1"}], tmp_path))
        assert out and out[0].caption == "cap"

    def test_render_with_cache_miss_writes(self, monkeypatch, tmp_path):
        from social_research_probe.technologies.charts.base import ChartResult

        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.get_json",
            lambda c, k: None,
        )
        captured = {}
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.set_json",
            lambda c, k, v: captured.update({"v": v}),
        )

        async def fake_render(items, out):
            return [ChartResult(path=str(tmp_path / "y.png"), caption="c")]

        monkeypatch.setattr(charts_svc.ChartsService, "_render", staticmethod(fake_render))
        out = asyncio.run(charts_svc.ChartsService._render_with_cache([{"id": "1"}], tmp_path))
        assert out[0].caption == "c"
        assert captured["v"]["captions"] == ["c"]


class TestStatisticsService:
    def test_compute_async(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        out = asyncio.run(stats_svc.StatisticsService._compute_async([]))
        assert out["highlights"] == []

    def test_cached_or_compute_hit(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.get_json",
            lambda c, k: {"highlights": ["h"], "low_confidence": False},
        )
        out = stats_svc.StatisticsService._cached_or_compute([{"id": "1"}])
        assert out["highlights"] == ["h"]

    def test_cached_or_compute_miss(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.get_json",
            lambda c, k: None,
        )
        captured = {}
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.set_json",
            lambda c, k, v: captured.update({"v": v}),
        )
        items = [
            {
                "overall_score": v,
                "trust": v,
                "trend": v,
                "opportunity": v,
                "features": {"view_velocity": v, "engagement_ratio": v, "age_days": v},
            }
            for v in (0.1, 0.2, 0.3, 0.4, 0.5)
        ]
        out = stats_svc.StatisticsService._cached_or_compute(items)
        assert out["highlights"]


class TestLLMSearchProvider:
    def test_health_check_no_runners(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.llm.registry.list_runners",
            lambda: [],
        )
        from social_research_probe.technologies.corroborates.llm_search import LLMSearchProvider

        assert LLMSearchProvider().health_check() is False

    def test_health_check_one_healthy(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.llm.registry.list_runners",
            lambda: ["claude"],
        )
        runner = MagicMock()
        runner.health_check.return_value = True
        monkeypatch.setattr(
            "social_research_probe.services.llm.registry.get_runner",
            lambda n: runner,
        )
        from social_research_probe.technologies.corroborates.llm_search import LLMSearchProvider

        assert LLMSearchProvider().health_check() is True

    def test_health_check_exception(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.llm.registry.list_runners",
            lambda: ["claude"],
        )

        def boom(n):
            raise RuntimeError("x")

        monkeypatch.setattr("social_research_probe.services.llm.registry.get_runner", boom)
        from social_research_probe.technologies.corroborates.llm_search import LLMSearchProvider

        assert LLMSearchProvider().health_check() is False

    def test_run_llm(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.llm.registry.run_with_fallback",
            lambda p, schema, preferred: {"verdict": "supported"},
        )
        cfg = MagicMock()
        cfg.llm_runner = "claude"
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            from social_research_probe.technologies.corroborates.llm_search import LLMSearchProvider

            out = LLMSearchProvider._run_llm("p")
        assert out == {"verdict": "supported"}
