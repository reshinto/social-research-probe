"""Tests for service class wrappers."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from social_research_probe.services.analyzing.charts import ChartsService
from social_research_probe.services.analyzing.statistics import StatisticsService
from social_research_probe.services.corroborating.corroborate import CorroborationService
from social_research_probe.services.enriching.summary import SummaryService
from social_research_probe.services.enriching.transcript import TranscriptService
from social_research_probe.services.llm import schemas
from social_research_probe.services.reporting.audio import AudioReportService
from social_research_probe.services.reporting.html import HtmlReportService
from social_research_probe.services.synthesizing.synthesis import SynthesisService


def test_schemas_present():
    assert schemas.TOPIC_SUGGESTIONS_SCHEMA["required"] == ["suggestions"]
    assert schemas.PURPOSE_SUGGESTIONS_SCHEMA["required"] == ["suggestions"]
    assert "topic" in schemas.NL_QUERY_CLASSIFICATION_SCHEMA["required"]


class TestChartsService:
    def test_no_techs(self):
        assert ChartsService()._get_technologies() == []

    def test_items_from_non_dict(self):
        assert ChartsService._items_from(None) == []

    def test_items_from_dict(self):
        assert ChartsService._items_from({"scored_items": [{"a": 1}, "skip"]}) == [{"a": 1}]

    def test_serialise_roundtrip(self, tmp_path):
        from social_research_probe.technologies.charts.base import ChartResult

        png = tmp_path / "x.png"
        png.write_bytes(b"\x89PNG")
        ch = ChartResult(path=str(png), caption="cap")
        out = ChartsService._serialise_results([ch], tmp_path)
        restored = ChartsService._restore_results(out, tmp_path)
        assert len(restored) == 1
        assert restored[0].caption == "cap"

    def test_restore_mismatch(self, tmp_path):
        out = ChartsService._restore_results({"filenames": ["x"], "captions": []}, tmp_path)
        assert out == []

    def test_restore_missing_file(self, tmp_path):
        out = ChartsService._restore_results(
            {"filenames": ["missing.png"], "captions": ["c"]}, tmp_path
        )
        assert out == []

    def test_execute_one_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(ChartsService().execute_one({"scored_items": []}))
        assert out.tech_results[0].success is True


class TestStatisticsService:
    def test_no_techs(self):
        assert StatisticsService()._get_technologies() == []

    def test_items_filter(self):
        assert StatisticsService._items({"scored_items": [{"a": 1}, "skip"]}) == [{"a": 1}]
        assert StatisticsService._items("notdict") == []

    def test_compute_empty(self):
        assert StatisticsService._compute([]) == {"highlights": [], "low_confidence": True}

    def test_compute_basic(self):
        items = [
            {
                "overall_score": v,
                "trust": v,
                "trend": v,
                "opportunity": v,
                "features": {"view_velocity": v, "engagement_ratio": v, "age_days": v},
            }
            for v in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
        ]
        out = StatisticsService._compute(items)
        assert out["low_confidence"] is False
        assert out["highlights"]

    def test_execute_one_basic(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(StatisticsService().execute_one({"scored_items": []}))
        assert out.tech_results[0].success is True

    def test_execute_one_failure(self, monkeypatch):
        async def boom(items):
            raise RuntimeError("nope")

        monkeypatch.setattr(StatisticsService, "_compute_async", staticmethod(boom))
        out = asyncio.run(StatisticsService().execute_one({"scored_items": [{"x": 1}]}))
        assert out.tech_results[0].success is False


class TestSynthesisService:
    def test_no_techs(self):
        assert SynthesisService()._get_technologies() == []

    def test_execute_failure(self):
        out = asyncio.run(SynthesisService().execute_one("not a dict"))
        assert out.tech_results


class TestCorroborationService:
    def test_no_techs(self):
        assert CorroborationService()._get_technologies() == []

    def test_execute_failure(self, monkeypatch):
        async def boom(claim, providers):
            raise RuntimeError("x")

        monkeypatch.setattr(
            "social_research_probe.services.corroborating.host.corroborate_claim", boom
        )
        cfg = MagicMock()
        cfg.corroboration_provider = "exa"
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(CorroborationService().execute_one({"title": "t"}))
        assert out.tech_results[0].success is False


class TestSummaryService:
    def test_no_techs(self):
        assert SummaryService()._get_technologies() == []

    def test_execute(self, monkeypatch):
        async def fake(prompt, task="generating response"):
            return "summary text"

        monkeypatch.setattr("social_research_probe.services.llm.ensemble.multi_llm_prompt", fake)
        out = asyncio.run(SummaryService().execute_one({"title": "t", "url": "https://x"}))
        assert out.tech_results[0].output == "summary text"

    def test_execute_failure(self, monkeypatch):
        async def fake(prompt, task="generating response"):
            raise RuntimeError("x")

        monkeypatch.setattr("social_research_probe.services.llm.ensemble.multi_llm_prompt", fake)
        out = asyncio.run(SummaryService().execute_one({"title": "t"}))
        assert out.tech_results[0].success is False


class TestTranscriptService:
    def test_techs(self):
        techs = TranscriptService()._get_technologies()
        assert techs and techs[0].name == "youtube_transcript_api"

    def test_execute_captions_path(self, monkeypatch):
        from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
            YoutubeTranscriptFetch,
        )

        async def fake_exec(self, data):
            return "transcript"

        monkeypatch.setattr(YoutubeTranscriptFetch, "execute", fake_exec)
        out = asyncio.run(TranscriptService().execute_one({"url": "u"}))
        assert any(r.output == "transcript" for r in out.tech_results)

    def test_execute_caption_failure(self, monkeypatch):
        from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
            YoutubeTranscriptFetch,
        )

        async def fake_exec(self, data):
            raise RuntimeError("fail")

        monkeypatch.setattr(YoutubeTranscriptFetch, "execute", fake_exec)
        out = asyncio.run(TranscriptService().execute_one({"url": "u"}))
        assert any(not r.success for r in out.tech_results)


class TestAudioReportService:
    def test_techs(self):
        techs = AudioReportService()._get_technologies()
        assert techs

    def test_execute_failure(self, monkeypatch):
        from social_research_probe.technologies.tts.voicebox import VoiceboxTTS

        async def fake_exec(self, data):
            raise RuntimeError("nope")

        monkeypatch.setattr(VoiceboxTTS, "execute", fake_exec)
        out = asyncio.run(AudioReportService().execute_one({"text": "x"}))
        assert out.tech_results[0].success is False


class TestHtmlReportService:
    def test_no_techs(self):
        assert HtmlReportService()._get_technologies() == []

    def test_execute_failure(self, monkeypatch):
        def boom(report):
            raise RuntimeError("nope")

        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube.write_html_report",
            boom,
        )
        out = asyncio.run(HtmlReportService().execute_one({"report": {}}))
        assert out.tech_results[0].success is False
