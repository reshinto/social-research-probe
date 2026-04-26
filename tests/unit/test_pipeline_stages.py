"""Unit tests for YouTube pipeline stage classes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from social_research_probe.platforms.base import EngagementMetrics, FetchLimits, RawItem
from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube.pipeline import (
    YouTubeAssembleStage,
    YouTubeChartsStage,
    YouTubeCorroborateStage,
    YouTubeFetchStage,
    YouTubeScoreStage,
    YouTubeStatsStage,
    YouTubeSummaryStage,
    YouTubeSynthesisStage,
    YouTubeTranscriptStage,
)
from social_research_probe.services.analyzing.charts import ChartsService
from social_research_probe.technologies.charts import selector as selector_mod
from social_research_probe.technologies.charts.base import ChartResult

_NOW = datetime(2026, 1, 2, tzinfo=UTC)


class _Cfg:
    def __init__(self, *, stages: dict[str, bool] | None = None) -> None:
        self._stages = stages or {}

    def stage_enabled(self, platform: str, name: str) -> bool:
        return self._stages.get(name, True)

    def service_enabled(self, name: str) -> bool:
        return True

    def technology_enabled(self, name: str) -> bool:
        return True


class _FakeConnector:
    default_limits = FetchLimits(max_items=1, recency_days=7)

    def find_by_topic(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        assert topic
        assert isinstance(limits, FetchLimits)
        return [_raw_item()]

    async def fetch_item_details(self, items: list[RawItem]) -> list[RawItem]:
        return items


def _raw_item(*, published_at: datetime | None = _NOW) -> RawItem:
    return RawItem(
        id="item-1",
        url="https://example.com/v/1",
        title="Video 1",
        author_id="chan-1",
        author_name="Channel 1",
        published_at=published_at,  # type: ignore[arg-type]
        metrics={"views": 1000, "likes": 50, "comments": 10},
        text_excerpt="Short excerpt",
        thumbnail=None,
        extras={},
    )


def _engagement() -> EngagementMetrics:
    return EngagementMetrics(
        views=1000,
        likes=100,
        comments=10,
        upload_date=_NOW,
        view_velocity=10.0,
        engagement_ratio=0.2,
        comment_velocity=1.0,
        cross_channel_repetition=0.0,
        raw={},
    )


def _state(
    *,
    platform: str = "youtube",
    platform_config: dict | None = None,
    stage_outputs: dict[str, dict] | None = None,
    topic: str = "AI",
    search_topic: str = "AI latest",
) -> PipelineState:
    state = PipelineState(
        platform_type=platform,
        cmd=SimpleNamespace(platform=platform),
        cache=None,
        platform_config=platform_config or {"enrich_top_n": 1},
        inputs={
            "topic": topic,
            "purpose_names": ["latest-news"],
            "search_topic": search_topic,
            "scoring_weights": {"trust": 0.4, "trend": 0.3, "opportunity": 0.3},
            "timings": {"stage_timings": []},
            "corroboration_backends": [],
        },
    )
    for name, data in (stage_outputs or {}).items():
        state.set_stage_output(name, data)
    return state


def _patch_cfg(monkeypatch, stages: dict[str, bool]) -> None:
    monkeypatch.setattr(
        "social_research_probe.config.load_active_config",
        lambda: _Cfg(stages=stages),
    )


# ---------------------------------------------------------------------------
# YouTubeFetchStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_stage_disabled_returns_empty(monkeypatch):
    _patch_cfg(monkeypatch, {"fetch": False})
    state = _state()
    await YouTubeFetchStage().execute(state)
    assert state.get_stage_output("fetch") == {"items": [], "engagement_metrics": []}


@pytest.mark.asyncio
async def test_fetch_stage_calls_connector(monkeypatch):
    import social_research_probe.services.sourcing.youtube as src_mod

    monkeypatch.setattr(src_mod, "YouTubeConnector", lambda cfg: _FakeConnector())
    state = _state()
    await YouTubeFetchStage().execute(state)

    fetch = state.get_stage_output("fetch")
    assert len(fetch["items"]) == 1
    assert fetch["items"][0].title == "Video 1"
    assert len(fetch["engagement_metrics"]) == 1


# ---------------------------------------------------------------------------
# YouTubeScoreStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_stage_disabled_passes_through_items(monkeypatch):
    _patch_cfg(monkeypatch, {"score": False})
    items = [_raw_item()]
    state = _state(stage_outputs={"fetch": {"items": items, "engagement_metrics": []}})
    await YouTubeScoreStage().execute(state)
    assert state.get_stage_output("score")["top_n"] == items


@pytest.mark.asyncio
async def test_score_stage_scores_items(monkeypatch):
    from social_research_probe.technologies.scoring import combine as combine_mod

    monkeypatch.setattr(combine_mod, "overall_score", lambda **kw: 0.75)

    items = [{"trust": 0.8, "trend": 0.5, "opportunity": 0.6}]
    state = _state(stage_outputs={"fetch": {"items": items, "engagement_metrics": []}})
    await YouTubeScoreStage().execute(state)
    score = state.get_stage_output("score")
    assert score["all_scored"][0]["overall_score"] == 0.75
    assert len(score["top_n"]) == 1


@pytest.mark.asyncio
async def test_score_stage_preserves_raw_items_as_scored_dicts(monkeypatch):
    from social_research_probe.technologies.scoring import combine as combine_mod

    monkeypatch.setattr(combine_mod, "overall_score", lambda **kw: 0.5)

    state = _state(stage_outputs={"fetch": {"items": [_raw_item()], "engagement_metrics": []}})
    await YouTubeScoreStage().execute(state)

    score = state.get_stage_output("score")
    assert len(score["top_n"]) == 1
    assert score["top_n"][0]["id"] == "item-1"
    assert score["top_n"][0]["title"] == "Video 1"
    assert score["top_n"][0]["overall_score"] == 0.5


# ---------------------------------------------------------------------------
# YouTubeTranscriptStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transcript_stage_disabled_passes_through(monkeypatch):
    _patch_cfg(monkeypatch, {"transcript": False})
    top_n = [{"title": "Video 1"}]
    state = _state(stage_outputs={"score": {"top_n": top_n}})
    await YouTubeTranscriptStage().execute(state)
    assert state.get_stage_output("transcript") == {"top_n": top_n}


@pytest.mark.asyncio
async def test_transcript_stage_empty_returns_immediately():
    state = _state(stage_outputs={"score": {"top_n": []}})
    await YouTubeTranscriptStage().execute(state)
    assert state.get_stage_output("transcript") == {"top_n": []}


# ---------------------------------------------------------------------------
# YouTubeSummaryStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_stage_disabled_passes_through(monkeypatch):
    _patch_cfg(monkeypatch, {"summary": False})
    top_n = [{"title": "Video 1"}]
    state = _state(stage_outputs={"transcript": {"top_n": top_n}})
    await YouTubeSummaryStage().execute(state)
    assert state.get_stage_output("summary") == {"top_n": top_n}


@pytest.mark.asyncio
async def test_summary_stage_empty_returns_immediately():
    state = _state(stage_outputs={"transcript": {"top_n": []}})
    await YouTubeSummaryStage().execute(state)
    assert state.get_stage_output("summary") == {"top_n": []}


# ---------------------------------------------------------------------------
# YouTubeCorroborateStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_corroborate_stage_skips_when_no_backends():
    top_n = [{"title": "Video 1"}]
    state = _state(stage_outputs={"summary": {"top_n": top_n}})
    state.inputs["corroboration_backends"] = []
    await YouTubeCorroborateStage().execute(state)
    assert state.get_stage_output("corroborate") == {"top_n": top_n}


@pytest.mark.asyncio
async def test_corroborate_stage_disabled_passes_through(monkeypatch):
    _patch_cfg(monkeypatch, {"corroborate": False})
    top_n = [{"title": "Video 1"}]
    state = _state(stage_outputs={"summary": {"top_n": top_n}})
    await YouTubeCorroborateStage().execute(state)
    assert state.get_stage_output("corroborate") == {"top_n": top_n}


# ---------------------------------------------------------------------------
# YouTubeStatsStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_stage_disabled_returns_empty(monkeypatch):
    _patch_cfg(monkeypatch, {"stats": False})
    state = _state(stage_outputs={"corroborate": {"top_n": [{"overall_score": 0.5}]}})
    await YouTubeStatsStage().execute(state)
    assert state.get_stage_output("stats") == {"stats_summary": {}}


# ---------------------------------------------------------------------------
# YouTubeChartsStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_charts_stage_disabled_returns_empty(monkeypatch):
    _patch_cfg(monkeypatch, {"charts": False})
    state = _state(stage_outputs={"corroborate": {"top_n": [{"overall_score": 0.5}]}})
    await YouTubeChartsStage().execute(state)
    out = state.get_stage_output("charts")
    assert out["chart_captions"] == []
    assert out["chart_takeaways"] == []


@pytest.mark.asyncio
async def test_charts_stage_carries_chart_caption(monkeypatch):
    @dataclass
    class _Chart:
        path: str
        caption: str

    class _ChartsService:
        async def execute_one(self, data):
            return SimpleNamespace(
                tech_results=[
                    SimpleNamespace(
                        success=True,
                        output=_Chart(path="/tmp/overall_score_bar.png", caption="Bar chart"),
                    )
                ]
            )

    import social_research_probe.services.analyzing.charts as charts_mod

    monkeypatch.setattr(charts_mod, "ChartsService", _ChartsService)
    state = _state(stage_outputs={"score": {"top_n": [{"overall_score": 0.5}]}})
    await YouTubeChartsStage().execute(state)

    out = state.get_stage_output("charts")
    assert out["chart_output"].path == "/tmp/overall_score_bar.png"
    assert out["chart_captions"] == ["Bar chart"]


@pytest.mark.asyncio
async def test_charts_service_writes_to_persistent_charts_dir(monkeypatch, tmp_data_dir):
    captured = {}

    def fake_select_and_render(data, label="values", output_dir=None):
        captured["data"] = data
        captured["label"] = label
        captured["output_dir"] = output_dir
        return ChartResult(
            path=f"{output_dir}/overall_score_bar.png",
            caption="Bar chart: overall_score (2 items)",
        )

    monkeypatch.setattr(selector_mod, "select_and_render", fake_select_and_render)

    result = await ChartsService().execute_one(
        {"scored_items": [{"overall_score": 0.25}, {"overall_score": 0.75}]}
    )

    chart = result.tech_results[0].output
    expected_dir = tmp_data_dir / "charts"
    assert captured == {
        "data": [0.25, 0.75],
        "label": "overall_score",
        "output_dir": str(expected_dir),
    }
    assert expected_dir.is_dir()
    assert chart.path == str(expected_dir / "overall_score_bar.png")
    assert f"_(see PNG: {chart.path})_" in chart.caption


# ---------------------------------------------------------------------------
# YouTubeSynthesisStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesis_stage_disabled_returns_empty(monkeypatch):
    _patch_cfg(monkeypatch, {"synthesis": False})
    state = _state(
        stage_outputs={
            "corroborate": {"top_n": []},
            "score": {"top_n": []},
            "fetch": {"items": [], "engagement_metrics": []},
            "stats": {"stats_summary": {}},
            "charts": {"chart_output": None, "chart_captions": [], "chart_takeaways": []},
        },
    )
    await YouTubeSynthesisStage().execute(state)
    assert state.get_stage_output("synthesis") == {"synthesis": ""}


# ---------------------------------------------------------------------------
# YouTubeAssembleStage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assemble_stage_builds_packet(monkeypatch):
    from social_research_probe.services.synthesizing import evidence as ev_mod
    from social_research_probe.services.synthesizing import formatter as fmt_mod

    monkeypatch.setattr(ev_mod, "summarize_engagement_metrics", lambda m: "0 items")
    monkeypatch.setattr(ev_mod, "summarize", lambda i, m, t, **kw: "evidence")
    monkeypatch.setattr(fmt_mod, "build_packet", lambda **kw: {**kw})

    state = _state(
        stage_outputs={
            "fetch": {"items": [], "engagement_metrics": []},
            "corroborate": {"top_n": []},
            "score": {"top_n": []},
            "stats": {"stats_summary": {}},
            "charts": {"chart_output": None, "chart_captions": [], "chart_takeaways": []},
        },
    )
    await YouTubeAssembleStage().execute(state)

    assemble_out = state.get_stage_output("assemble")
    assert "packet" in assemble_out
    assert assemble_out["packet"]["topic"] == "AI"
