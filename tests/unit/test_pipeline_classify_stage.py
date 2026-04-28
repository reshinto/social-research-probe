"""Tests for YouTubeClassifyStage."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

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
    cfg.tunables = {}
    monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)

    cmd = MagicMock()
    cmd.platform = "youtube"
    state = PipelineState(
        platform_type="youtube",
        cmd=cmd,
        cache=None,
        platform_config={},
        inputs={"topic": "ai", "purpose_names": []},
    )
    return state, cfg


def _mk_result(output: str) -> ServiceResult:
    return ServiceResult(
        service_name="youtube.classifying.source_class",
        input_key="x",
        tech_results=[
            TechResult(tech_name="t", input=None, output=output, success=True),
        ],
    )


class TestStageDisabled:
    def test_stage_disabled_returns_items_unchanged(self, enabled_state, monkeypatch):
        state, cfg = enabled_state
        cfg.stage_enabled.return_value = False
        state.set_stage_output("fetch", {"items": [{"id": "1", "channel": "BBC News"}]})

        out = asyncio.run(yt.YouTubeClassifyStage().execute(state))
        items = out.get_stage_output("classify")["items"]
        assert items == [{"id": "1", "channel": "BBC News"}]

    def test_no_items_short_circuits(self, enabled_state):
        state, _ = enabled_state
        state.set_stage_output("fetch", {"items": []})
        out = asyncio.run(yt.YouTubeClassifyStage().execute(state))
        assert out.get_stage_output("classify")["items"] == []

    def test_service_gate_disabled_marks_all_unknown(self, enabled_state):
        state, cfg = enabled_state
        cfg.service_enabled.return_value = False
        state.set_stage_output("fetch", {"items": [{"id": "1", "channel": "BBC News"}]})

        out = asyncio.run(yt.YouTubeClassifyStage().execute(state))
        items = out.get_stage_output("classify")["items"]
        assert items[0]["source_class"] == "unknown"


class TestStageEnabled:
    def test_classifies_via_service(self, enabled_state, monkeypatch):
        state, _ = enabled_state
        state.set_stage_output(
            "fetch", {"items": [{"id": "1", "channel": "BBC News", "title": "x"}]}
        )

        async def fake(self, data):
            return _mk_result("primary")

        from social_research_probe.services.classifying.source_class import SourceClassService

        monkeypatch.setattr(SourceClassService, "execute_one", fake)

        out = asyncio.run(yt.YouTubeClassifyStage().execute(state))
        items = out.get_stage_output("classify")["items"]
        assert items[0]["source_class"] == "primary"

    def test_caches_per_channel(self, enabled_state, monkeypatch):
        state, _ = enabled_state
        state.set_stage_output(
            "fetch",
            {
                "items": [
                    {"id": "1", "channel": "Indie", "title": "a"},
                    {"id": "2", "channel": "Indie", "title": "b"},
                    {"id": "3", "channel": "Indie", "title": "c"},
                ]
            },
        )

        calls = {"n": 0}

        async def fake_execute_one(self, data):
            calls["n"] += 1
            return _mk_result("secondary")

        from social_research_probe.services.classifying.source_class import SourceClassService

        monkeypatch.setattr(SourceClassService, "execute_one", fake_execute_one)

        out = asyncio.run(yt.YouTubeClassifyStage().execute(state))
        items = out.get_stage_output("classify")["items"]
        assert len(items) == 3
        assert all(it["source_class"] == "secondary" for it in items)
        assert calls["n"] == 1

    def test_preserves_existing_classification(self, enabled_state, monkeypatch):
        state, _ = enabled_state
        state.set_stage_output(
            "fetch",
            {"items": [{"id": "1", "channel": "X", "source_class": "primary", "title": "y"}]},
        )

        async def fail(*a, **kw):
            raise AssertionError("service should not be called")

        from social_research_probe.services.classifying.source_class import SourceClassService

        monkeypatch.setattr(SourceClassService, "execute_one", fail)

        out = asyncio.run(yt.YouTubeClassifyStage().execute(state))
        items = out.get_stage_output("classify")["items"]
        assert items[0]["source_class"] == "primary"

    def test_title_override_promotes_to_commentary(self, enabled_state, monkeypatch):
        state, _ = enabled_state
        state.set_stage_output(
            "fetch",
            {"items": [{"id": "1", "channel": "BBC News", "title": "My reaction"}]},
        )

        async def fake(self, data):
            return _mk_result("primary")

        from social_research_probe.services.classifying.source_class import SourceClassService

        monkeypatch.setattr(SourceClassService, "execute_one", fake)

        out = asyncio.run(yt.YouTubeClassifyStage().execute(state))
        items = out.get_stage_output("classify")["items"]
        assert items[0]["source_class"] == "commentary"


class TestStaticHelpers:
    def test_channel_of_prefers_channel(self):
        assert yt.YouTubeClassifyStage._channel_of({"channel": "A", "author_name": "B"}) == "A"

    def test_channel_of_falls_back_to_author_name(self):
        assert yt.YouTubeClassifyStage._channel_of({"author_name": "B"}) == "B"

    def test_channel_of_empty(self):
        assert yt.YouTubeClassifyStage._channel_of({}) == ""

    def test_output_class_picks_first_success(self):
        result = ServiceResult(
            service_name="s",
            input_key="x",
            tech_results=[
                TechResult(tech_name="a", input=None, output=None, success=False),
                TechResult(tech_name="b", input=None, output="primary", success=True),
            ],
        )
        assert yt.YouTubeClassifyStage._output_class(result) == "primary"

    def test_output_class_unknown_when_no_success(self):
        result = ServiceResult(
            service_name="s",
            input_key="x",
            tech_results=[
                TechResult(tech_name="a", input=None, output=None, success=False),
            ],
        )
        assert yt.YouTubeClassifyStage._output_class(result) == "unknown"
