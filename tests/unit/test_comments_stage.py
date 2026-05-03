"""Tests for YouTubeCommentsStage in platforms/youtube."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

import social_research_probe.platforms.youtube as yt
from social_research_probe.platforms.state import PipelineState
from social_research_probe.services import ServiceResult, TechResult


@pytest.fixture
def enabled_state(monkeypatch):
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.service_enabled.return_value = True
    cfg.technology_enabled.return_value = True
    monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
    cmd = MagicMock()
    cmd.platform = "youtube"
    state = PipelineState(
        platform_type="youtube",
        cmd=cmd,
        cache=None,
        platform_config={"enrich_top_n": 2, "include_shorts": True, "allow_html": False},
        inputs={"topic": "ai"},
    )
    return state


def _mk_comments_result(item_output):
    return ServiceResult(
        service_name="youtube.enriching.comments",
        input_key="x",
        tech_results=[
            TechResult(tech_name="youtube_comments", input=None, output=item_output, success=True)
        ],
    )


class TestCommentsStage:
    def test_stage_name(self):
        assert yt.YouTubeCommentsStage().stage_name == "comments"

    def test_enabled_fetches_comments(self, enabled_state, monkeypatch):
        item = {"id": "vid1", "title": "T"}
        enabled_state.set_stage_output("transcript", {"top_n": [item]})
        enriched = {
            **item,
            "comments": ["Nice"],
            "source_comments": [],
            "comments_status": "available",
        }

        async def fake_one(self, i):
            return _mk_comments_result(enriched)

        monkeypatch.setattr(
            "social_research_probe.services.enriching.comments.CommentsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        top_n = out.get_stage_output("comments")["top_n"]
        assert top_n[0]["comments_status"] == "available"
        assert top_n[0]["comments"] == ["Nice"]

    def test_disabled_marks_items(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("transcript", {"top_n": [{"id": "v1"}, {"id": "v2"}]})
        monkeypatch.setattr(
            "social_research_probe.config.load_active_config",
            lambda *a, **k: MagicMock(stage_enabled=lambda *a, **k: False),
        )
        out = asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        top_n = out.get_stage_output("comments")["top_n"]
        assert all(it["comments_status"] == "disabled" for it in top_n)

    def test_empty_top_n(self, enabled_state):
        enabled_state.set_stage_output("transcript", {"top_n": []})
        out = asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        assert out.get_stage_output("comments")["top_n"] == []

    def test_max_videos_respected(self, enabled_state, monkeypatch):
        items = [{"id": f"v{i}"} for i in range(4)]
        enabled_state.set_stage_output("transcript", {"top_n": items})
        enabled_state.platform_config["comments"] = {"max_videos": 2}
        called_ids = []

        async def fake_one(self, item):
            called_ids.append(item["id"])
            return _mk_comments_result({**item, "comments_status": "available"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.comments.CommentsService.execute_one",
            fake_one,
        )
        asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        assert called_ids == ["v0", "v1"]

    def test_items_beyond_max_videos_get_not_attempted(self, enabled_state, monkeypatch):
        items = [{"id": f"v{i}"} for i in range(3)]
        enabled_state.set_stage_output("transcript", {"top_n": items})
        enabled_state.platform_config["comments"] = {"max_videos": 1}

        async def fake_one(self, item):
            return _mk_comments_result({**item, "comments_status": "available"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.comments.CommentsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        top_n = out.get_stage_output("comments")["top_n"]
        assert top_n[1]["comments_status"] == "not_attempted"
        assert top_n[2]["comments_status"] == "not_attempted"

    def test_service_no_output_falls_back_to_failed(self, enabled_state, monkeypatch):
        item = {"id": "vid1"}
        enabled_state.set_stage_output("transcript", {"top_n": [item]})

        async def fake_one(self, i):
            return ServiceResult(
                service_name="youtube.enriching.comments",
                input_key="vid1",
                tech_results=[TechResult("youtube_comments", None, None, success=False)],
            )

        monkeypatch.setattr(
            "social_research_probe.services.enriching.comments.CommentsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        top_n = out.get_stage_output("comments")["top_n"]
        assert top_n[0]["comments_status"] == "failed"
        assert top_n[0]["id"] == "vid1"

    def test_non_dict_items_do_not_crash(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("transcript", {"top_n": ["not-a-dict", {"id": "v1"}]})

        async def fake_one(self, item):
            return _mk_comments_result({**item, "comments_status": "available"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.comments.CommentsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        top_n = out.get_stage_output("comments")["top_n"]
        assert len(top_n) == 1
        assert top_n[0]["comments_status"] == "available"

    def test_config_values_passed_to_service(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output("transcript", {"top_n": [{"id": "v1"}]})
        enabled_state.platform_config["comments"] = {
            "max_videos": 5,
            "max_comments_per_video": 10,
            "order": "time",
        }
        received = {}

        async def fake_one(self, item):
            received["max"] = item.get("_max_comments")
            received["order"] = item.get("_order")
            return _mk_comments_result({**item, "comments_status": "available"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.comments.CommentsService.execute_one",
            fake_one,
        )
        asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        assert received["max"] == 10
        assert received["order"] == "time"

    def test_comments_runs_when_transcript_disabled(self, enabled_state, monkeypatch):
        enabled_state.set_stage_output(
            "transcript",
            {"top_n": [{"id": "v1", "title": "T", "transcript_status": "disabled"}]},
        )

        async def fake_one(self, item):
            return _mk_comments_result({**item, "comments_status": "available"})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.comments.CommentsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeCommentsStage().execute(enabled_state))
        top_n = out.get_stage_output("comments")["top_n"]
        assert top_n[0]["comments_status"] == "available"
        assert top_n[0]["transcript_status"] == "disabled"


class TestPipelineStagesWiring:
    def test_pipeline_includes_comments_stage(self):
        stages = yt.YouTubePipeline().stages()
        stage_names = [s.stage_name for group in stages for s in group]
        assert "comments" in stage_names

    def test_comments_stage_before_summary(self):
        stages = yt.YouTubePipeline().stages()
        flat = [s.stage_name for group in stages for s in group]
        assert flat.index("comments") < flat.index("summary")

    def test_comments_stage_after_transcript(self):
        stages = yt.YouTubePipeline().stages()
        flat = [s.stage_name for group in stages for s in group]
        assert flat.index("transcript") < flat.index("comments")
