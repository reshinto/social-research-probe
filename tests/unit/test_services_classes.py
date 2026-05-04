"""Tests for service class wrappers."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.services import BaseService
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

    def test_render_charts_no_success(self, monkeypatch):
        from social_research_probe.services import ServiceResult, TechResult

        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        failed_tr = TechResult(
            tech_name="charts_suite", input={}, output=None, success=False, error="err"
        )
        svc_result = ServiceResult(
            service_name="charts", input_key="scored_items", tech_results=[failed_tr]
        )
        out = (
            asyncio.run(
                ChartsService().execute_service({"scored_items": [{"score": 1}]}, svc_result)
            )
            .tech_results[0]
            .output
        )
        assert out == {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []}

    def test_execute_service_with_empty_result_sets_input_key(self):
        from social_research_probe.services import ServiceResult

        result = asyncio.run(
            ChartsService().execute_service(
                {"scored_items": []},
                ServiceResult(service_name="charts", input_key="x", tech_results=[]),
            )
        )
        assert result.input_key == "scored_items"

    def test_render_charts_disabled(self, monkeypatch):
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        with patch.object(ChartsService, "is_enabled", return_value=False):
            out = asyncio.run(ChartsService().execute_one({"scored_items": [{"score": 1}]}))
        assert out.tech_results == []

    def test_render_charts_success(self, tmp_path, monkeypatch):
        from social_research_probe.technologies.charts import ChartResult

        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        cr = ChartResult(path=str(tmp_path / "bar.png"), caption="Bar chart")
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with (
            patch("social_research_probe.config.load_active_config", return_value=cfg),
            patch(
                "social_research_probe.technologies.charts.render_charts",
                return_value=[cr],
            ),
        ):
            result = asyncio.run(ChartsService().execute_one({"scored_items": [{"score": 1}]}))
            out = result.tech_results[0].output
        assert out["chart_outputs"] == [cr]
        assert out["chart_captions"] == ["Bar chart"]
        assert out["chart_takeaways"] == []


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
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda: cfg)
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
        assert out.tech_results[0].output["summary"] == "summary text"

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
        assert out.tech_results[0].output["summary"] == "one two three"

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
        assert any(r.output.get("transcript") == "transcript" for r in out.tech_results)

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

    def test_execute_fallback_exhausts_all_failing(self, monkeypatch):
        from social_research_probe.services import ServiceResult

        svc = AudioReportService()

        class DummyTech:
            def __init__(self, name):
                self.name = name
                self.caller_service = ""

            async def execute(self, data):
                return None

        monkeypatch.setattr(svc, "_get_technologies", lambda: [DummyTech("t1"), DummyTech("t2")])
        result = asyncio.run(
            svc.execute_service(
                "x", ServiceResult(service_name="audio", input_key="x", tech_results=[])
            )
        )
        assert len(result.tech_results) == 2
        assert not result.tech_results[0].success
        assert not result.tech_results[1].success

    def test_execute_fallback_no_technologies(self, monkeypatch):
        from social_research_probe.services import ServiceResult

        svc = AudioReportService()
        monkeypatch.setattr(svc, "_get_technologies", lambda: [])
        result = asyncio.run(
            svc.execute_service(
                "x", ServiceResult(service_name="audio", input_key="x", tech_results=[])
            )
        )
        assert len(result.tech_results) == 0

    def test_execute_fallback_success(self, monkeypatch):
        from social_research_probe.services import ServiceResult

        svc = AudioReportService()

        class DummyTech:
            def __init__(self, name):
                self.name = name
                self.caller_service = ""

            async def execute(self, data):
                return "audio_data"

        monkeypatch.setattr(svc, "_get_technologies", lambda: [DummyTech("t1")])
        result = asyncio.run(
            svc.execute_service(
                "x", ServiceResult(service_name="audio", input_key="x", tech_results=[])
            )
        )
        assert result.tech_results[0].success
        assert result.tech_results[0].output == "audio_data"

    def test_execute_fallback_with_pre_populated_result(self):
        from social_research_probe.services import ServiceResult, TechResult

        svc = AudioReportService()
        pre_tr = TechResult(tech_name="pre", input="x", output="audio", success=True)
        result = asyncio.run(
            svc.execute_service(
                {"text": "x"},
                ServiceResult(service_name="audio", input_key="x", tech_results=[pre_tr]),
            )
        )
        assert len(result.tech_results) == 1
        assert result.tech_results[0].tech_name == "pre"


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


class TestBaseService:
    def _make_simple(self, *, concurrent=False):
        class Simple(BaseService):
            service_name = "simple"
            enabled_config_key = ""
            run_technologies_concurrently = concurrent

            def _get_technologies(self):
                return [None]

            async def execute_service(self, data, result):
                return result

        return Simple

    def test_subclass_cannot_override_execute_batch(self):
        with pytest.raises(TypeError, match="execute_batch"):

            class Bad(BaseService):
                service_name = "bad"
                enabled_config_key = ""

                def _get_technologies(self):
                    return [None]

                async def execute_service(self, data, result):
                    return result

                async def execute_batch(self, inputs):  # forbidden
                    return []

    def test_subclass_cannot_override_execute_one(self):
        with pytest.raises(TypeError, match="execute_one"):

            class Bad(BaseService):
                service_name = "bad"
                enabled_config_key = ""

                def _get_technologies(self):
                    return [None]

                async def execute_service(self, data, result):
                    return result

                async def execute_one(self, data):  # forbidden
                    return None

    def test_is_enabled_returns_true_when_no_key(self):
        svc_class = self._make_simple()
        assert svc_class.is_enabled() is True

    def test_execute_batch_runs_all_inputs(self):
        svc_class = self._make_simple()
        results = asyncio.run(svc_class().execute_batch(["a", "b", "c"]))
        assert len(results) == 3

    def test_concurrent_raises_when_get_technologies_empty(self):
        class BadTech(BaseService):
            service_name = "bad"
            enabled_config_key = ""
            run_technologies_concurrently = True

            def _get_technologies(self):
                return []

            async def execute_service(self, data, result):
                return result

        with pytest.raises(ValueError, match="_get_technologies"):
            asyncio.run(BadTech().execute_one("x"))

    def test_concurrent_catches_tech_exception(self):
        class RaisingTech:
            name = "raiser"
            caller_service = ""

            async def execute(self, data):
                raise RuntimeError("tech error")

        class ConcurrentSvc(BaseService):
            service_name = "concurrent"
            enabled_config_key = ""
            run_technologies_concurrently = True

            def _get_technologies(self):
                return [RaisingTech()]

            async def execute_service(self, data, result):
                return result

        result = asyncio.run(ConcurrentSvc().execute_one("x"))
        assert result.tech_results[0].success is False
        assert result.tech_results[0].error == "tech error"
