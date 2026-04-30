"""Tests for service class wrappers."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from social_research_probe.services.analyzing.charts import ChartsService
from social_research_probe.services.analyzing.statistics import StatisticsService
from social_research_probe.services.corroborating.corroborate import CorroborationService
from social_research_probe.services.enriching.summary import (
    SummaryService,
    _configured_word_limit,
    _with_summary_word_limit,
)
from social_research_probe.services.enriching.transcript import TranscriptService
from social_research_probe.services.reporting.audio import AudioReportService
from social_research_probe.services.reporting.html import HtmlReportService
from social_research_probe.services.synthesizing.synthesis import SynthesisService
from social_research_probe.technologies.charts import items_from
from social_research_probe.technologies.enriching import _coerce_word_limit
from social_research_probe.technologies.llms import schemas
from social_research_probe.technologies.statistics import _compute, items_from_data


def test_schemas_present():
    assert schemas.TOPIC_SUGGESTIONS_SCHEMA["required"] == ["suggestions"]
    assert schemas.PURPOSE_SUGGESTIONS_SCHEMA["required"] == ["suggestions"]
    assert "topic" in schemas.NL_QUERY_CLASSIFICATION_SCHEMA["required"]


class TestChartsService:
    def test_techs(self):
        techs = ChartsService()._get_technologies()
        assert techs[0].name == "charts_suite"

    def test_items_from_non_dict(self):
        assert items_from(None) == []

    def test_items_from_dict(self):
        assert items_from({"scored_items": [{"a": 1}, "skip"]}) == [{"a": 1}]

    def test_execute_one_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(ChartsService().execute_one({"scored_items": []}))
        assert out.tech_results[0].success is True


class TestStatisticsService:
    def test_techs(self):
        techs = StatisticsService()._get_technologies()
        assert techs[0].name == "stats_per_target"

    def test_items_filter(self):
        assert items_from_data({"scored_items": [{"a": 1}, "skip"]}) == [{"a": 1}]
        assert items_from_data("notdict") == []

    def test_compute_empty(self):
        assert _compute([]) == {"highlights": [], "low_confidence": True}

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
        out = _compute(items)
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

        monkeypatch.setattr("social_research_probe.technologies.statistics.compute_async", boom)
        out = asyncio.run(StatisticsService().execute_one({"scored_items": [{"x": 1}]}))
        assert out.tech_results[0].success is False


class TestSynthesisService:
    def test_techs(self):
        techs = SynthesisService()._get_technologies()
        assert techs[0].name == "llm_synthesis"

    def test_execute_failure(self, monkeypatch):
        async def boom(prompt, task="generating response"):
            raise RuntimeError("nope")

        monkeypatch.setattr(
            "social_research_probe.technologies.llms.ensemble.multi_llm_prompt", boom
        )
        out = asyncio.run(SynthesisService().execute_one("not a dict"))
        assert out.tech_results[0].success is False


class TestCorroborationService:
    def _patch_auto_init(self, monkeypatch):
        cfg = MagicMock()
        cfg.corroboration_provider = "exa"
        monkeypatch.setattr(
            "social_research_probe.config.load_active_config", lambda: cfg
        )
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.select_healthy_providers",
            lambda configured: (["exa"], ("exa",)),
        )
        monkeypatch.setattr(
            "social_research_probe.utils.display.fast_mode.fast_mode_enabled",
            lambda: False,
        )

    def test_techs(self, monkeypatch):
        self._patch_auto_init(monkeypatch)
        techs = CorroborationService()._get_technologies()
        assert techs[0].name == "corroboration_host"

    def test_execute_failure(self, monkeypatch):
        self._patch_auto_init(monkeypatch)

        async def boom(claim, providers):
            raise RuntimeError("x")

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim", boom
        )
        out = asyncio.run(CorroborationService().execute_one({"title": "t"}))
        assert out.tech_results[0].success is False


class TestSummaryService:
    def test_techs(self):
        techs = SummaryService()._get_technologies()
        assert techs[0].name == "llm_ensemble"

    def test_execute(self, monkeypatch):
        async def fake(prompt, task="generating response"):
            return "summary text"

        monkeypatch.setattr(
            "social_research_probe.technologies.llms.ensemble.multi_llm_prompt", fake
        )
        out = asyncio.run(SummaryService().execute_one({"title": "t", "url": "https://x"}))
        assert out.tech_results[0].output == "summary text"

    def test_execute_uses_configured_word_limit(self, monkeypatch):
        cfg = MagicMock()
        cfg.tunables = {"per_item_summary_words": 3}
        cfg.service_enabled.return_value = True
        cfg.technology_enabled.return_value = True
        cfg.debug_enabled.return_value = False

        prompts = []

        async def fake(prompt, task="generating response"):
            prompts.append(prompt)
            return "one two three four five"

        monkeypatch.setattr(
            "social_research_probe.technologies.llms.ensemble.multi_llm_prompt", fake
        )
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(SummaryService().execute_one({"title": "t", "url": "https://x"}))

        assert "at most 3 words" in prompts[0]
        assert out.tech_results[0].output == "one two three"

    def test_configured_word_limit_falls_back_on_bad_config(self):
        cfg = MagicMock()
        cfg.tunables = {"per_item_summary_words": object()}
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            assert _configured_word_limit() == 100

    def test_configured_word_limit_falls_back_on_non_positive_config(self):
        cfg = MagicMock()
        cfg.tunables = {"per_item_summary_words": 0}
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            assert _configured_word_limit() == 100

    def test_with_summary_word_limit_passes_through_non_dict(self):
        assert _with_summary_word_limit("raw") == "raw"

    def test_coerce_word_limit_falls_back_for_invalid_value(self):
        assert _coerce_word_limit("not-int") == 100

    def test_execute_failure(self, monkeypatch):
        async def fake(prompt, task="generating response"):
            raise RuntimeError("x")

        monkeypatch.setattr(
            "social_research_probe.technologies.llms.ensemble.multi_llm_prompt", fake
        )
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
    def test_techs(self):
        techs = HtmlReportService()._get_technologies()
        assert techs[0].name == "html_render"

    def test_execute_failure(self, monkeypatch):
        def boom(report):
            raise RuntimeError("nope")

        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube.write_html_report",
            boom,
        )
        out = asyncio.run(HtmlReportService().execute_one({"report": {}}))
        assert out.tech_results[0].success is False
