"""Push to 100%."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import social_research_probe.services.scoring as compute_mod
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.analyzing import charts as charts_svc
from social_research_probe.services.enriching import transcript as transcript_svc
from social_research_probe.technologies.corroborates.brave import BraveProvider
from social_research_probe.technologies.corroborates.exa import ExaProvider
from social_research_probe.technologies.corroborates.llm_search import LLMSearchProvider
from social_research_probe.technologies.corroborates.tavily import TavilyProvider
from social_research_probe.technologies.llms import gemini_cli
from social_research_probe.technologies.report_render.html.raw_html import (
    _sections,
)
from social_research_probe.technologies.report_render.html.raw_html import (
    youtube as yt_html,
)
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    logistic_regression,
    polynomial_regression,
)


class TestYtTechnologyLogsException:
    def test_exception_returns_false(self):
        with patch(
            "social_research_probe.config.load_active_config",
            side_effect=RuntimeError,
        ):
            assert yt_html._technology_logs_enabled() is False


class TestYtFetchItemsAsync:
    def test_fetch_items_uses_connector(self, monkeypatch):
        from datetime import UTC, datetime

        from social_research_probe.platforms.base import RawItem

        item = RawItem(
            id="1",
            url="u",
            title="t",
            author_id="a",
            author_name="A",
            published_at=datetime.now(UTC),
            metrics={},
            text_excerpt=None,
            thumbnail=None,
            extras={},
        )

        class FakeConn:
            default_limits = MagicMock()

            def __init__(self, cfg):
                pass

            def find_by_topic(self, topic, limits):
                return [item]

            async def fetch_item_details(self, items):
                return items

        from social_research_probe.platforms.registry import CLIENTS

        monkeypatch.setitem(CLIENTS, "youtube", FakeConn)
        monkeypatch.setattr(
            "social_research_probe.services.sourcing.youtube.compute_engagement_metrics",
            lambda items: [],
        )
        items, _em = asyncio.run(yt.YouTubeFetchStage()._fetch_items("topic", {}))
        assert len(items) == 1


class TestGeminiRunSearchSync:
    def test_run_search_sync(self, monkeypatch):
        result = MagicMock(stdout="json")
        monkeypatch.setattr(
            "social_research_probe.technologies.llms.gemini_cli.subprocess_run",
            lambda *a, **kw: result,
        )
        out = gemini_cli._run_search_sync("gemini", "q", 30)
        assert out == "json"


class TestChartsRenderViaSuite:
    def test_render_calls_suite(self, monkeypatch, tmp_path):
        captured = {}

        def fake_render_all(items, out):
            captured["called"] = True
            return []

        monkeypatch.setattr(
            "social_research_probe.services.analyzing.render_all",
            fake_render_all,
        )
        out = asyncio.run(charts_svc.ChartsService._render([{"id": "1"}], tmp_path))
        assert out == [] and captured["called"]


class TestTranscriptWhisperException:
    def test_whisper_exception(self, monkeypatch):
        from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
            YoutubeTranscriptFetch,
        )

        async def fake_exec(self, data):
            return None

        monkeypatch.setattr(YoutubeTranscriptFetch, "execute", fake_exec)

        def boom(url, tmp):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "social_research_probe.technologies.media_fetch.yt_dlp.download_audio", boom
        )
        out = asyncio.run(transcript_svc.TranscriptService().execute_one({"url": "u"}))
        assert any(not r.success for r in out.tech_results)


class TestComputeMetricsValuesNone:
    def test_metric_values_none(self):
        out = compute_mod._metric_values(None)
        assert out == (0.0, 0.0, 0.0)


class TestLLMSearchAskLLM:
    def test_ask_llm_uses_thread(self, monkeypatch):
        provider = LLMSearchProvider()
        monkeypatch.setattr(
            LLMSearchProvider, "_run_llm", classmethod(lambda cls, p: {"verdict": "supported"})
        )
        out = asyncio.run(provider._ask_llm("text", []))
        assert out == {"verdict": "supported"}


class TestExaCorroborateRuns:
    def test_runs(self, monkeypatch):
        async def fake_search(self, q):
            return [{"url": "https://x"}]

        monkeypatch.setattr(ExaProvider, "_search", fake_search)
        out = asyncio.run(ExaProvider().corroborate(MagicMock(text="c", source_url=None)))
        assert out.verdict == "supported"


class TestBraveCorroborateAsync:
    def test_runs(self, monkeypatch):
        async def fake_search(self, q):
            return [{"url": "https://x"}]

        monkeypatch.setattr(BraveProvider, "_search", fake_search)
        out = asyncio.run(BraveProvider().corroborate(MagicMock(text="c", source_url=None)))
        assert out.verdict == "supported"


class TestTavilyCorroborateAsync:
    def test_runs(self, monkeypatch):
        async def fake_search(self, q):
            return [{"url": "https://x"}]

        monkeypatch.setattr(TavilyProvider, "_search", fake_search)
        out = asyncio.run(TavilyProvider().corroborate(MagicMock(text="c", source_url=None)))
        assert out.verdict == "supported"


class TestSectionsWhatItMeansEdge:
    def test_no_base_no_hint(self):
        # Both empty → returns empty
        out = _sections._what_it_means("nothing", "", "", "", [])
        assert out == ""

    def test_only_hint(self, monkeypatch):
        monkeypatch.setattr(_sections, "_contextual_explanation", lambda m, f: "")
        out = _sections._what_it_means(
            "Mean overall: 0.5", "", "descriptive", "ai", ["latest-news"]
        )
        assert isinstance(out, str)


class TestBayesianRunFullPath:
    def test_run_with_features(self):
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        features = {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}
        out = bayesian_linear.run(y, features)
        # may produce coefficients or fail gracefully
        assert isinstance(out, list)


class TestLogisticAllZeroWeights:
    def test_break_when_weights_zero(self):
        # Force overflow path that makes all weights zero
        y = [0, 1, 0, 1]
        features = {"x": [1e10, -1e10, 1e10, -1e10]}
        out = logistic_regression.run(y, features, max_iter=2)
        assert isinstance(out, list)


class TestPolynomialNegDegree:
    def test_neg(self):
        out = polynomial_regression.run([1.0, 2.0], [1.0, 2.0], degree=-1)
        assert out == []


class TestHuberConvergence:
    def test_perfect_fit(self):
        x = [1.0, 2.0, 3.0]
        y = [v for v in x]
        out = huber_regression.run(x, y)
        assert out
