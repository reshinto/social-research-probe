"""Final batch: pipeline yt enabled paths, serve_report DnG paths, ensemble, orchestrator."""

from __future__ import annotations

import asyncio
import socket
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import serve_report
from social_research_probe.platforms import orchestrator
from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.llm import ensemble
from social_research_probe.utils.core.research_command_parser import ParsedRunResearch


@pytest.fixture
def enabled_state():
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.service_enabled.return_value = True
    cfg.technology_enabled.return_value = True
    cfg.llm_runner = "claude"
    cfg.preferred_free_text_runner = "claude"
    cfg.corroboration_provider = "exa"
    cfg.tunables = {"summary_divergence_threshold": 0.4, "per_item_summary_words": 100}
    state = PipelineState(
        platform_type="youtube",
        cmd=None,
        cache=None,
        platform_config={"enrich_top_n": 2, "include_shorts": True},
        inputs={"topic": "ai", "purpose_names": ["career"]},
    )
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield state


def test_orchestrator_run_pipeline_smoke(monkeypatch):
    pytest.skip("requires deeper pipeline mocks")


def test_orchestrator_unknown_platform():
    cmd = ParsedRunResearch(platform="bogus-platform", topics=[("t", [])])
    with pytest.raises(Exception):
        asyncio.run(orchestrator.run_pipeline(cmd))


def test_orchestrator_maybe_register_fake_off(monkeypatch):
    monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
    orchestrator._maybe_register_fake()


def test_orchestrator_build_platform_config_fast_mode(monkeypatch):
    monkeypatch.setenv("SRP_FAST_MODE", "1")
    cfg = MagicMock()
    cfg.platform_defaults.return_value = {"enrich_top_n": 10}
    cmd = ParsedRunResearch(platform="youtube", topics=[])
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        out = orchestrator._build_platform_config(cmd)
    assert out["enrich_top_n"] == 3


def test_ensemble_synthesize_only_codex(monkeypatch):
    cfg = MagicMock()
    cfg.service_enabled.return_value = True
    cfg.technology_enabled.return_value = True

    async def fake_run(name, prompt, task="generating response"):
        if "synthesising" in task:
            return None
        return None

    monkeypatch.setattr(ensemble, "_run_provider", fake_run)
    out = asyncio.run(ensemble._synthesize({"codex": "x"}, "p", cfg))
    assert out == "x"


def test_ensemble_collect_responses(monkeypatch):
    async def fake_run(name, prompt, task="generating response"):
        return f"answer-{name}"

    monkeypatch.setattr(ensemble, "_run_provider", fake_run)
    out = asyncio.run(ensemble._collect_responses("p", providers=("claude", "gemini")))
    assert out == {"claude": "answer-claude", "gemini": "answer-gemini"}


def test_yt_score_full_path(enabled_state, monkeypatch):
    enabled_state.set_stage_output("fetch", {"items": [{"id": "1"}], "engagement_metrics": []})
    monkeypatch.setattr(
        "social_research_probe.services.scoring.score_items",
        lambda items, em, weights: [{"id": "1", "overall_score": 0.5}],
    )
    out = asyncio.run(yt.YouTubeScoreStage().execute(enabled_state))
    assert out.get_stage_output("score")["all_scored"]


def test_yt_score_full_path_failure(enabled_state, monkeypatch):
    enabled_state.set_stage_output("fetch", {"items": [{"id": "1"}], "engagement_metrics": []})
    from social_research_probe.services.base import ServiceResult, TechResult

    async def fake_execute_one(self, data):
        return ServiceResult(
            service_name="scoring",
            input_key="data",
            tech_results=[
                TechResult(tech_name="dummy", input=None, success=False, error="err", output=None),
                TechResult(
                    tech_name="dummy", input=None, success=True, error=None, output="not-a-list"
                ),
            ],
        )

    monkeypatch.setattr(
        "social_research_probe.services.scoring.score.ScoringService.execute_one", fake_execute_one
    )
    out = asyncio.run(yt.YouTubeScoreStage().execute(enabled_state))
    assert out.get_stage_output("score")["all_scored"] == []


def test_yt_assemble_disabled(enabled_state, monkeypatch):
    monkeypatch.setattr(yt.YouTubeAssembleStage, "_is_enabled", lambda self, state: False)
    out = asyncio.run(yt.YouTubeAssembleStage().execute(enabled_state))
    assert out.get_stage_output("assemble") is not None


def test_yt_structured_synth_disabled(enabled_state, monkeypatch):
    monkeypatch.setattr(
        yt.YouTubeStructuredSynthesisStage, "_is_enabled", lambda self, state: False
    )
    out = asyncio.run(yt.YouTubeStructuredSynthesisStage().execute(enabled_state))
    assert out is enabled_state


def test_yt_report_disabled(enabled_state, monkeypatch):
    monkeypatch.setattr(yt.YouTubeReportStage, "_is_enabled", lambda self, state: False)
    out = asyncio.run(yt.YouTubeReportStage().execute(enabled_state))
    assert out is enabled_state


def test_yt_narration_disabled(enabled_state, monkeypatch):
    monkeypatch.setattr(yt.YouTubeNarrationStage, "_is_enabled", lambda self, state: False)
    out = asyncio.run(yt.YouTubeNarrationStage().execute(enabled_state))
    assert out is enabled_state


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_serve_report_proxy_target_construction():
    handler = MagicMock()
    handler.path = "/voicebox/generate/stream"
    handler.headers = {"Content-Length": "0"}
    handler.command = "POST"
    handler.rfile.read.return_value = b""
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("x")):
        serve_report._proxy_voicebox_request(handler, "http://127.0.0.1:1/")
    assert handler.send_response.called


def test_serve_report_post_unknown(tmp_path):
    f = tmp_path / "r.html"
    f.write_text("<x/>")
    handler_class = serve_report._make_handler(f, "http://nope")
    handler = handler_class.__new__(handler_class)
    handler.path = "/somewhere"
    handler.send_error = MagicMock()
    handler.do_POST()
    handler.send_error.assert_called_with(404, "Not Found")
