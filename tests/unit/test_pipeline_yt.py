"""Tests for platforms/youtube/pipeline stage names + disabled paths."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.utils.purposes.merge import MergedPurpose


@pytest.fixture
def disabled_state():
    cfg = MagicMock()
    cfg.stage_enabled.return_value = False
    cfg.service_enabled.return_value = False
    state = PipelineState(
        platform_type="youtube",
        cmd=None,
        cache=None,
        inputs={"topic": "ai", "purpose_names": ["career"]},
    )
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield state


def test_stage_names():
    assert yt.YouTubeFetchStage().stage_name == "fetch"
    assert yt.YouTubeScoreStage().stage_name == "score"
    assert yt.YouTubeTranscriptStage().stage_name == "transcript"
    assert yt.YouTubeSummaryStage().stage_name == "summary"
    assert yt.YouTubeCorroborateStage().stage_name == "corroborate"
    assert yt.YouTubeStatsStage().stage_name == "stats"
    assert yt.YouTubeChartsStage().stage_name == "charts"
    assert yt.YouTubeSynthesisStage().stage_name == "synthesis"
    assert yt.YouTubeAssembleStage().stage_name == "assemble"
    assert yt.YouTubeStructuredSynthesisStage().stage_name == "structured_synthesis"
    assert yt.YouTubeReportStage().stage_name == "report"
    assert yt.YouTubeNarrationStage().stage_name == "narration"


def test_fetch_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeFetchStage().execute(disabled_state))
    assert out.get_stage_output("fetch") == {"items": [], "engagement_metrics": []}


def test_score_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeScoreStage().execute(disabled_state))
    assert "all_scored" in out.get_stage_output("score")


def test_transcript_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeTranscriptStage().execute(disabled_state))
    assert out.get_stage_output("transcript") is not None


def test_summary_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeSummaryStage().execute(disabled_state))
    assert out.get_stage_output("summary") is not None


def test_corroborate_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeCorroborateStage().execute(disabled_state))
    assert out.get_stage_output("corroborate") is not None


def test_stats_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeStatsStage().execute(disabled_state))
    assert out.get_stage_output("stats") is not None


def test_charts_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeChartsStage().execute(disabled_state))
    assert out.get_stage_output("charts") is not None


def test_synthesis_disabled(disabled_state):
    out = asyncio.run(yt.YouTubeSynthesisStage().execute(disabled_state))
    assert out.get_stage_output("synthesis") is not None


def test_resolve_search_topic_no_purpose(disabled_state):
    state = disabled_state
    assert yt.YouTubeFetchStage()._resolve_search_topic(state) == "ai"


def test_resolve_search_topic_with_purpose(disabled_state):
    state = disabled_state
    state.inputs["merged_purpose"] = MergedPurpose(
        names=("career",), method="track latest", evidence_priorities=()
    )
    out = yt.YouTubeFetchStage()._resolve_search_topic(state)
    assert "ai" in out


def test_score_top_n_limit(disabled_state):
    disabled_state.platform_config["enrich_top_n"] = 7
    assert yt.YouTubeScoreStage()._top_n_limit(disabled_state) == 7


def test_score_resolve_weights_none(disabled_state):
    assert yt.YouTubeScoreStage()._resolve_purpose_scoring_weights(disabled_state) is None


def test_pipeline_construct():
    p = yt.YouTubePipeline()
    assert hasattr(p, "stages")


def test_pipeline_run_dispatches(monkeypatch):
    cfg = MagicMock()
    cfg.stage_enabled.return_value = False
    cfg.service_enabled.return_value = False
    state = PipelineState(
        platform_type="youtube",
        cmd=None,
        cache=None,
        inputs={"topic": "x", "purpose_names": ["p"]},
    )
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        out = asyncio.run(yt.YouTubePipeline().run(state))
    assert out is state
