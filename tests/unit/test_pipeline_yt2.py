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
                        output={
                            "all_scored": [{"id": "1", "overall_score": 0.5}],
                            "top_n": [{"id": "1", "overall_score": 0.5}],
                        },
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
        sr = _mk_service_result(
            "transcript",
            {"url": "u1", "transcript": "TRANSCRIPT", "transcript_status": "available"},
        )

        async def fake_one(self, item):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.enriching.transcript.TranscriptService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        assert out.get_stage_output("transcript")["top_n"][0]["transcript"] == "TRANSCRIPT"

    def test_enabled_empty_top_n(self, enabled_state):
        enabled_state.set_stage_output("score", {"top_n": []})
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        assert out.get_stage_output("transcript")["top_n"] == []

    def test_enabled_sets_available_status(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"url": "u1"}]})
        sr = _mk_service_result(
            "transcript",
            {"url": "u1", "transcript": "TRANSCRIPT", "transcript_status": "available"},
        )

        async def fake_one(self, item):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.enriching.transcript.TranscriptService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        top_n = out.get_stage_output("transcript")["top_n"]
        assert top_n[0]["transcript_status"] == "available"

    def test_skips_non_dict_items(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": ["not-a-dict"]})

        async def fail(self, item):
            raise AssertionError("service should not be called for non-dict items")

        monkeypatch.setattr(
            "social_research_probe.services.enriching.transcript.TranscriptService.execute_one",
            fail,
        )
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        assert out.get_stage_output("transcript")["top_n"] == []

    def test_sets_failed_status_when_transcript_service_errors(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"url": "u1"}]})
        sr = ServiceResult(
            service_name="transcript",
            input_key="u1",
            tech_results=[
                TechResult(
                    tech_name="t",
                    input=None,
                    output={"url": "u1", "transcript_status": "failed"},
                    success=False,
                    error="boom",
                )
            ],
        )

        async def fake_one(self, item):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.enriching.transcript.TranscriptService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        top_n = out.get_stage_output("transcript")["top_n"]
        assert top_n[0]["transcript_status"] == "failed"

    def test_sets_unavailable_status_when_no_transcript_output(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"url": "u1"}]})
        sr = ServiceResult(
            service_name="transcript",
            input_key="u1",
            tech_results=[
                TechResult(
                    tech_name="t",
                    input=None,
                    output={"url": "u1", "transcript_status": "unavailable"},
                    success=False,
                )
            ],
        )

        async def fake_one(self, item):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.enriching.transcript.TranscriptService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        top_n = out.get_stage_output("transcript")["top_n"]
        assert top_n[0]["transcript_status"] == "unavailable"

    def test_omits_transcript_result_without_item_output(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"url": "u1"}]})
        sr = ServiceResult(
            service_name="transcript",
            input_key="u1",
            tech_results=[TechResult(tech_name="t", input=None, output=None, success=False)],
        )

        async def fake_one(self, item):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.enriching.transcript.TranscriptService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        assert out.get_stage_output("transcript")["top_n"] == []

    def test_disabled_sets_disabled_status(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("score", {"top_n": [{"url": "u1"}, {"url": "u2"}]})
        cfg = MagicMock()
        cfg.stage_enabled.return_value = False
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        out = asyncio.run(yt.YouTubeTranscriptStage().execute(enabled_state))
        top_n = out.get_stage_output("transcript")["top_n"]
        assert all(it["transcript_status"] == "disabled" for it in top_n)
        assert "transcript" not in top_n[0]


class TestSummaryStage:
    def test_enabled(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("comments", {"top_n": [{"url": "u1"}]})
        sr = _mk_service_result("summary", {"url": "u1", "summary": "SUM"})

        async def fake_one(self, item):
            return sr

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        assert out.get_stage_output("summary")["top_n"][0]["summary"] == "SUM"

    def test_empty_top_n(self, enabled_state):
        enabled_state.set_stage_output("comments", {"top_n": []})
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        assert out.get_stage_output("summary")["top_n"] == []

    def test_attaches_text_surrogate(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output(
            "comments", {"top_n": [{"url": "u1", "title": "T", "transcript": "txt"}]}
        )
        calls = []

        async def fake_summary_one(self, item):
            return _mk_service_result("summary", {**item, "summary": "SUM"})

        async def fake_surrogate_one(self, item):
            calls.append(item)
            return _mk_service_result(
                "text_surrogate",
                {
                    "primary_text": item["transcript"],
                    "primary_text_source": "transcript",
                    "evidence_tier": "metadata_transcript",
                },
            )

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_one",
            fake_summary_one,
        )
        monkeypatch.setattr(
            "social_research_probe.services.enriching.text_surrogate.TextSurrogateService.execute_one",
            fake_surrogate_one,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        top_n = out.get_stage_output("summary")["top_n"]
        assert calls == [{"url": "u1", "title": "T", "transcript": "txt"}]
        assert "text_surrogate" in top_n[0]
        assert top_n[0]["text_surrogate"]["primary_text"] == "txt"

    def test_skips_non_dict_items_in_surrogate_build(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output(
            "comments", {"top_n": [{"url": "u1", "title": "T"}, "not-a-dict"]}
        )

        async def fake_summary_one(self, item):
            return _mk_service_result("summary", {**item, "summary": "SUM"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_one",
            fake_summary_one,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        top_n = out.get_stage_output("summary")["top_n"]
        assert "text_surrogate" in top_n[0]
        assert top_n[1] == "not-a-dict"

    def test_skips_text_surrogate_when_service_disabled(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("comments", {"top_n": [{"url": "u1", "title": "T"}]})
        cfg = MagicMock()
        cfg.stage_enabled.return_value = True
        cfg.service_enabled.side_effect = lambda name: name != "text_surrogate"
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)

        async def fake_summary_one(self, item):
            return _mk_service_result("summary", {"url": "u1", "summary": "SUM"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_one",
            fake_summary_one,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        top_n = out.get_stage_output("summary")["top_n"]
        assert "text_surrogate" not in top_n[0]
        assert "evidence_tier" not in top_n[0]

    def test_attaches_evidence_tier(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("comments", {"top_n": [{"url": "u1", "title": "T"}]})

        async def fake_one(self, item):
            return _mk_service_result("summary", {**item, "summary": "SUM"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        top_n = out.get_stage_output("summary")["top_n"]
        assert "evidence_tier" in top_n[0]
        assert top_n[0]["evidence_tier"] == "metadata_only"

    def test_keeps_item_when_summary_service_returns_no_output(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("comments", {"top_n": [{"url": "u1", "title": "T"}]})

        async def fake_one(self, item):
            return ServiceResult(service_name="summary", input_key="T", tech_results=[])

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        top_n = out.get_stage_output("summary")["top_n"]
        assert top_n[0]["title"] == "T"
        assert "summary" not in top_n[0]

    def test_evidence_tier_upgrades_with_comments(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output(
            "comments",
            {
                "top_n": [
                    {
                        "id": "v1",
                        "title": "T",
                        "comments": ["Nice!"],
                        "comments_status": "available",
                    }
                ]
            },
        )

        async def fake_one(self, item):
            return _mk_service_result("summary", {**item, "summary": "SUM"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.summary.SummaryService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeSummaryStage().execute(enabled_state))
        top_n = out.get_stage_output("summary")["top_n"]
        assert top_n[0]["evidence_tier"] == "metadata_comments"


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

        async def fake_one(self, item):
            return _mk_service_result("corroboration", {"id": "1", "corroboration": "ok"})

        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.__init__",
            lambda self: setattr(self, "providers", ["exa"]) or None,
        )
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeCorroborateStage().execute(enabled_state))
        assert out.get_stage_output("corroborate")["top_n"][0]["corroboration"] == "ok"

    def test_execute_with_no_healthy_providers_passes_through(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("summary", {"top_n": [{"id": "1"}]})
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.__init__",
            lambda self: setattr(self, "providers", []) or None,
        )
        out = asyncio.run(yt.YouTubeCorroborateStage().execute(enabled_state))
        assert out.get_stage_output("corroborate")["top_n"] == [{"id": "1"}]

    def test_execute_skips_non_dict_items(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("summary", {"top_n": ["not-a-dict"]})
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.__init__",
            lambda self: setattr(self, "providers", ["exa"]) or None,
        )

        async def fail(self, item):
            raise AssertionError("service should not be called for non-dict items")

        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.execute_one",
            fail,
        )
        out = asyncio.run(yt.YouTubeCorroborateStage().execute(enabled_state))
        assert out.get_stage_output("corroborate")["top_n"] == []

    def test_omits_corroboration_result_without_item_output(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("summary", {"top_n": [{"id": "1"}]})

        async def fake_one(self, item):
            return ServiceResult(
                service_name="corroboration",
                input_key="x",
                tech_results=[TechResult("t", None, None, success=False)],
            )

        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.__init__",
            lambda self: setattr(self, "providers", ["exa"]) or None,
        )
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeCorroborateStage().execute(enabled_state))
        assert out.get_stage_output("corroborate")["top_n"] == []


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

        sr = _mk_service_result(
            "charts",
            {"chart_outputs": [FakeChart()], "chart_captions": ["c1"], "chart_takeaways": []},
        )

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
                tech_results=[
                    TechResult(tech_name="t", input=None, output="synth-text", success=True)
                ],
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
            {"summary_divergence": 0.6, "title": "t", "transcript": "text"},
            {"summary_divergence": 0.1, "transcript": "text"},
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

    def test_compose_research_report_data_non_zero_validation(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.synthesizing.synthesis.helpers.evidence.summarize",
            lambda items, metrics, top_n: "evidence",
        )
        monkeypatch.setattr(
            "social_research_probe.services.synthesizing.synthesis.helpers.evidence.summarize_engagement_metrics",
            lambda metrics: "engagement",
        )
        top_n = [
            {"source_class": "primary", "corroboration": {"aggregate_verdict": "supported"}},
            {"source_class": "secondary", "corroboration": {"aggregate_verdict": "inconclusive"}},
        ]
        report = yt.YouTubeAssembleStage()._compose_research_report_data(
            topic="test",
            platform="youtube",
            purpose_names=["explore"],
            top_n=top_n,
            items=[],
            engagement_metrics=[],
            stats_summary={},
            chart_captions=[],
            chart_takeaways=[],
            warnings=[],
        )
        svs = report["source_validation_summary"]
        assert svs["validated"] == 1
        assert svs["unverified"] == 1
        assert svs["primary"] == 1
        assert svs["secondary"] == 1

    def test_compose_defensive_recomputation_fires(self, monkeypatch):
        zero_svs = {
            "validated": 0,
            "partially": 0,
            "unverified": 0,
            "low_trust": 0,
            "primary": 0,
            "secondary": 0,
            "commentary": 0,
            "notes": "",
        }
        fake_report = {
            "topic": "test",
            "platform": "youtube",
            "purpose_set": [],
            "items_top_n": [],
            "source_validation_summary": zero_svs,
            "platform_engagement_summary": "",
            "evidence_summary": "",
            "stats_summary": {},
            "chart_captions": [],
            "chart_takeaways": [],
            "warnings": [],
        }
        monkeypatch.setattr(
            "social_research_probe.utils.report.formatter.build_report",
            lambda **kwargs: dict(fake_report),
        )
        monkeypatch.setattr(
            "social_research_probe.services.synthesizing.synthesis.helpers.evidence.summarize",
            lambda items, metrics, top_n: "",
        )
        monkeypatch.setattr(
            "social_research_probe.services.synthesizing.synthesis.helpers.evidence.summarize_engagement_metrics",
            lambda metrics: "",
        )
        top_n = [{"source_class": "primary", "corroboration": {"aggregate_verdict": "supported"}}]
        report = yt.YouTubeAssembleStage()._compose_research_report_data(
            topic="test",
            platform="youtube",
            purpose_names=[],
            top_n=top_n,
            items=[],
            engagement_metrics=[],
            stats_summary={},
            chart_captions=[],
            chart_takeaways=[],
            warnings=[],
        )
        assert report["source_validation_summary"]["validated"] == 1


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

        def fake_write_final_report(report, *, allow_html=True):
            return "/tmp/rep.html"

        monkeypatch.setattr(
            "social_research_probe.services.reporting.write_final_report",
            fake_write_final_report,
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
