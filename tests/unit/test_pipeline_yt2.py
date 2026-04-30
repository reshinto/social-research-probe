"""Comprehensive tests for platforms/youtube/pipeline enabled-paths."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services import ServiceResult, TechResult


@pytest.fixture
def enabled_state(monkeypatch):
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.service_enabled.return_value = True
    cfg.technology_enabled.return_value = True
    cfg.corroboration_provider = "exa"
    cfg.tunables = {"summary_divergence_threshold": 0.4}
    monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)

    cmd = MagicMock()
    cmd.platform = "youtube"
    state = PipelineState(
        platform_type="youtube",
        cmd=cmd,
        cache=None,
        platform_config={"enrich_top_n": 2, "include_shorts": True, "allow_html": False},
        inputs={"topic": "ai", "purpose_names": ["career"]},
    )
    return state


def _mk_service_result(name, output, success=True):
    return ServiceResult(
        service_name=name,
        input_key="x",
        tech_results=[TechResult(tech_name=name, input=None, output=output, success=success)],
    )


class TestFetchStage:
    def test_enabled_path(self, enabled_state, monkeypatch):
        async def fake_fetch(self, topic, cfg):
            return [{"id": "1"}], [{"v": 1}]

        monkeypatch.setattr(yt.YouTubeFetchStage, "_fetch_items", fake_fetch)
        out = asyncio.run(yt.YouTubeFetchStage().execute(enabled_state))
        assert out.get_stage_output("fetch")["items"] == [{"id": "1"}]


class TestScoreStage:
    def test_enabled_with_items(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("fetch", {"items": [{"id": "1"}], "engagement_metrics": []})
        from social_research_probe.services import ServiceResult, TechResult

        async def fake_one(self, data):
            return ServiceResult(
                service_name="scoring",
                input_key="items",
                tech_results=[
                    TechResult(
                        tech_name="t",
                        input=None,
                        output=[{"id": "1", "overall_score": 0.5}],
                        success=True,
                    )
                ],
            )

        monkeypatch.setattr(
            "social_research_probe.services.scoring.score.ScoringService.execute_one", fake_one
        )
        out = asyncio.run(yt.YouTubeScoreStage().execute(enabled_state))
        assert out.get_stage_output("score")["all_scored"]

    def test_enabled_no_items(self, enabled_state):
        enabled_state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        out = asyncio.run(yt.YouTubeScoreStage().execute(enabled_state))
        assert out.get_stage_output("score")["all_scored"] == []

    def test_score_resolve_weights_with_purpose(self, enabled_state, monkeypatch):
        from social_research_probe.utils.purposes.merge import MergedPurpose

        enabled_state.inputs["merged_purpose"] = MergedPurpose(
            names=("c",), method="m", evidence_priorities=()
        )
        monkeypatch.setattr(
            "social_research_probe.services.scoring.resolve_scoring_weights",
            lambda m: {"trust": 0.5},
        )
        out = yt.YouTubeScoreStage()._resolve_purpose_scoring_weights(enabled_state)
        assert out["trust"] == 0.5


class TestTranscriptStage:
    def test_enabled_with_results(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"url": "u1"}]})
        sr = _mk_service_result("transcript", "TRANSCRIPT")

        async def fake_batch(self, items):
            return [sr]

        monkeypatch.setattr(
            "social_research_probe.services.enriching.transcript.TranscriptService.execute_batch",
            fake_batch,
        )
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        assert out.get_stage_output("transcript")["top_n"][0]["transcript"] == "TRANSCRIPT"

    def test_enabled_empty_top_n(self, enabled_state):
        enabled_state.set_stage_output("score", {"top_n": []})
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        assert out.get_stage_output("transcript")["top_n"] == []


class TestSummaryStage:
    def test_enabled(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("transcript", {"top_n": [{"url": "u1"}]})
        sr = _mk_service_result("summary", "SUM")

        async def fake_batch(self, items):
            return [sr]

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_batch",
            fake_batch,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        assert out.get_stage_output("summary")["top_n"][0]["summary"] == "SUM"

    def test_empty_top_n(self, enabled_state):
        enabled_state.set_stage_output("transcript", {"top_n": []})
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        assert out.get_stage_output("summary")["top_n"] == []


class TestCorroborateStage:
    def test_execute_disabled_or_empty(self, enabled_state):
        enabled_state.set_stage_output("summary", {"top_n": []})
        out = asyncio.run(yt.YouTubeCorroborateStage().execute(enabled_state))
        assert out.get_stage_output("corroborate")["top_n"] == []

    def test_service_none_provider_returns_empty_providers(self, monkeypatch):
        from social_research_probe.services.corroborating import select_healthy_providers

        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.corroboration_provider = "none"
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            healthy, _ = select_healthy_providers("none")
        assert healthy == []

    def test_execute_with_providers(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("summary", {"top_n": [{"id": "1"}]})

        async def fake_batch(self, top_n):
            return [{"id": "1", "corroboration": "ok"}]

        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.__init__",
            lambda self: setattr(self, "providers", ["exa"]) or None,
        )
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.corroborate_batch",
            fake_batch,
        )
        out = asyncio.run(yt.YouTubeCorroborateStage().execute(enabled_state))
        assert out.get_stage_output("corroborate")["top_n"][0]["corroboration"] == "ok"


class TestStatsStage:
    def test_enabled(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"x": 1}]})
        sr = _mk_service_result("stats", {"highlights": ["h"]})

        async def fake_one(self, data):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.analyzing.statistics.StatisticsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeStatsStage().execute(enabled_state))
        assert out.get_stage_output("stats")["stats_summary"]["highlights"] == ["h"]

    def test_enabled_failure(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"x": 1}]})
        sr = ServiceResult("stats", "x", [TechResult("t", None, None, success=False)])

        async def fake_one(self, data):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.analyzing.statistics.StatisticsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeStatsStage().execute(enabled_state))
        assert out.get_stage_output("stats")["stats_summary"] == {}


class TestChartsStage:
    def test_enabled(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"all_scored": [{"x": 1}]})

        class FakeChart:
            caption = "c1"

        sr = _mk_service_result("charts", [FakeChart()])

        async def fake_one(self, data):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.analyzing.charts.ChartsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeChartsStage().execute(enabled_state))
        assert out.get_stage_output("charts")["chart_captions"] == ["c1"]


class TestSynthesisStage:
    def test_build_context(self, enabled_state):
        enabled_state.set_stage_output("score", {"top_n": [{"x": 1}]})
        enabled_state.set_stage_output("corroborate", {"top_n": [{"y": 1}]})
        enabled_state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        enabled_state.set_stage_output("stats", {"stats_summary": {}})
        enabled_state.set_stage_output("charts", {"chart_outputs": []})
        out = yt.YouTubeSynthesisStage()._build_synthesis_context(enabled_state)
        assert out["topic"] == "ai" and out["top_n"] == [{"y": 1}]

    def test_execute_enabled(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": []})
        enabled_state.set_stage_output("corroborate", {"top_n": []})
        enabled_state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        enabled_state.set_stage_output("stats", {"stats_summary": {}})
        enabled_state.set_stage_output("charts", {"chart_outputs": []})

        async def fake_execute_one(self, data):
            from social_research_probe.services import ServiceResult, TechResult

            return ServiceResult(
                service_name="synthesis",
                input_key="context",
                tech_results=[TechResult(tech_name="t", input=None, output="synth-text", success=True)],
            )

        monkeypatch.setattr(
            "social_research_probe.services.synthesizing.synthesis.SynthesisService.execute_one",
            fake_execute_one,
        )
        out = asyncio.run(yt.YouTubeSynthesisStage().execute(enabled_state))
        assert out.get_stage_output("synthesis")["synthesis"] == "synth-text"


class TestAssembleStage:
    def test_collect_divergence_warnings(self):
        from social_research_probe.utils.pipeline.helpers import collect_divergence_warnings

        items = [
            {"summary_divergence": 0.6, "title": "t"},
            {"summary_divergence": 0.1},
            {},
        ]
        out = collect_divergence_warnings(items, 0.4)
        assert len(out) == 1

    def test_execute_enabled(self, enabled_state):
        enabled_state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        enabled_state.set_stage_output(
            "score", {"top_n": [{"id": "1", "title": "t", "channel": "c", "url": "u"}]}
        )
        enabled_state.set_stage_output("corroborate", {"top_n": []})
        enabled_state.set_stage_output("stats", {"stats_summary": {}})
        enabled_state.set_stage_output("charts", {"chart_captions": [], "chart_takeaways": []})
        out = asyncio.run(yt.YouTubeAssembleStage().execute(enabled_state))
        assert out.outputs["report"]["topic"] == "ai"


class TestBuildSourceValidationSummary:
    def test_counts_verdicts_and_classes(self):
        top_n = [
            {
                "source_class": "primary",
                "corroboration": {"aggregate_verdict": "supported"},
            },
            {
                "source_class": "secondary",
                "corroboration": {"aggregate_verdict": "refuted"},
            },
            {
                "source_class": "commentary",
                "corroboration": {"aggregate_verdict": "inconclusive"},
            },
            {"source_class": "unknown"},
        ]
        stage = yt.YouTubeAssembleStage()
        svs = stage._build_source_validation_summary(top_n)
        assert svs["validated"] == 1
        assert svs["low_trust"] == 1
        assert svs["unverified"] == 2
        assert svs["partially"] == 0
        assert svs["primary"] == 1
        assert svs["secondary"] == 1
        assert svs["commentary"] == 1

    def test_empty_list(self):
        svs = yt.YouTubeAssembleStage()._build_source_validation_summary([])
        assert svs["validated"] == 0
        assert svs["primary"] == 0


class TestStructuredSynthesisStage:
    def test_enabled(self, enabled_state, monkeypatch):
        enabled_state.outputs["report"] = {}
        called = []
        monkeypatch.setattr(
            "social_research_probe.services.synthesizing.runner.attach_synthesis",
            lambda r: called.append(True),
        )
        asyncio.run(yt.YouTubeStructuredSynthesisStage().execute(enabled_state))
        assert called == [True]


class TestReportStage:
    def test_enabled(self, enabled_state, monkeypatch):
        enabled_state.outputs["report"] = {}

        async def fake_write_report(self, report, *, allow_html=True):
            return "/tmp/rep.html"

        monkeypatch.setattr(
            "social_research_probe.services.reporting.report.ReportService.write_report",
            fake_write_report,
        )
        out = asyncio.run(yt.YouTubeReportStage().execute(enabled_state))
        assert out.outputs["report"]["report_path"] == "/tmp/rep.html"


class TestNarrationStage:
    def test_enabled_no_text(self, enabled_state):
        enabled_state.outputs["report"] = {"evidence_summary": ""}
        out = asyncio.run(yt.YouTubeNarrationStage().execute(enabled_state))
        assert out is enabled_state

    def test_enabled_with_text(self, enabled_state, monkeypatch):
        enabled_state.outputs["report"] = {"evidence_summary": "x"}

        async def fake_one(self, data):
            return _mk_service_result("audio", "ok")

        monkeypatch.setattr(
            "social_research_probe.services.reporting.audio.AudioReportService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeNarrationStage().execute(enabled_state))
        assert out is enabled_state


class TestPipelineRun:
    def test_full_run_disabled(self, enabled_state, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.config.load_active_config",
            lambda *a, **k: MagicMock(
                stage_enabled=lambda *a, **k: False, service_enabled=lambda *a, **k: False
            ),
        )
        out = asyncio.run(yt.YouTubePipeline().run(enabled_state))
        assert out is enabled_state
