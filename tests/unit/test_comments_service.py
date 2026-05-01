"""Tests for CommentsService in services/enriching/comments.py."""

from __future__ import annotations

import asyncio

import pytest

from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.services.enriching.comments import CommentsService


def _ok_result(comments):
    return ServiceResult(
        service_name=CommentsService.service_name,
        input_key="vid1",
        tech_results=[
            TechResult(
                tech_name="youtube_comments",
                input="vid1",
                output=comments,
                success=True,
            )
        ],
    )


def _fail_result():
    return ServiceResult(
        service_name=CommentsService.service_name,
        input_key="vid1",
        tech_results=[
            TechResult(
                tech_name="youtube_comments",
                input="vid1",
                output=None,
                success=False,
            )
        ],
    )


def _run(coro):
    return asyncio.run(coro)


def _sample_comments():
    return [
        {"comment_id": "c1", "author": "Alice", "text": "Great video!", "like_count": 5,
         "published_at": "2026-01-01T00:00:00Z", "source_id": "vid1", "platform": "youtube"},
    ]


class TestCommentsServiceMeta:
    def test_service_name(self):
        assert CommentsService.service_name == "youtube.enriching.comments"

    def test_enabled_config_key(self):
        assert CommentsService.enabled_config_key == "services.youtube.enriching.comments"


class TestCommentsServiceTechnologies:
    def test_get_technologies_returns_youtube_comments_tech(self):
        from social_research_probe.technologies.media_fetch import YouTubeCommentsTech

        techs = CommentsService()._get_technologies()
        assert len(techs) == 1
        assert isinstance(techs[0], YouTubeCommentsTech)


class TestCommentsServiceExecuteService:
    @pytest.fixture()
    def svc(self):
        return CommentsService()

    @pytest.mark.asyncio
    async def test_successful_comments_available(self, svc):
        item = {"id": "vid1", "title": "Test"}
        comments = _sample_comments()
        result = await svc.execute_service(item, _ok_result(comments))
        out = result.tech_results[0].output
        assert out["comments_status"] == "available"
        assert out["source_comments"] == comments
        assert out["comments"] == ["Great video!"]

    @pytest.mark.asyncio
    async def test_comments_is_flat_strings(self, svc):
        item = {"id": "vid1"}
        comments = _sample_comments()
        result = await svc.execute_service(item, _ok_result(comments))
        out = result.tech_results[0].output
        assert isinstance(out["comments"], list)
        assert all(isinstance(c, str) for c in out["comments"])

    @pytest.mark.asyncio
    async def test_source_comments_is_structured(self, svc):
        item = {"id": "vid1"}
        comments = _sample_comments()
        result = await svc.execute_service(item, _ok_result(comments))
        out = result.tech_results[0].output
        assert isinstance(out["source_comments"], list)
        assert "comment_id" in out["source_comments"][0]

    @pytest.mark.asyncio
    async def test_empty_comments_unavailable(self, svc):
        item = {"id": "vid1", "title": "Test"}
        result = await svc.execute_service(
            item,
            ServiceResult(
                service_name=svc.service_name,
                input_key="vid1",
                tech_results=[
                    TechResult(
                        tech_name="youtube_comments", input="vid1", output=[], success=True
                    )
                ],
            ),
        )
        out = result.tech_results[0].output
        assert out["comments_status"] == "unavailable"
        assert out["source_comments"] == []
        assert out["comments"] == []

    @pytest.mark.asyncio
    async def test_tech_failure_returns_failed(self, svc):
        item = {"id": "vid1", "title": "Test"}
        result = await svc.execute_service(item, _fail_result())
        out = result.tech_results[0].output
        assert out["comments_status"] == "failed"
        assert out["source_comments"] == []
        assert out["comments"] == []

    @pytest.mark.asyncio
    async def test_missing_video_id_returns_unavailable(self, svc):
        item = {"title": "No URL or ID"}
        result = await svc.execute_service(
            item,
            ServiceResult(service_name=svc.service_name, input_key="", tech_results=[]),
        )
        out = result.tech_results[0].output
        assert out["comments_status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_non_dict_input_no_crash(self, svc):
        result = await svc.execute_service(
            "not-a-dict",
            ServiceResult(service_name=svc.service_name, input_key="", tech_results=[]),
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_max_comments_and_order_passed_to_tech(self, svc):
        item = {"id": "vid42", "_max_comments": 10, "_order": "time"}
        received = {}

        class FakeTech:
            name = "youtube_comments"
            caller_service = None

            async def execute(self, data):
                received["data"] = data
                return []

        svc._get_technologies = lambda: [FakeTech()]
        await svc.execute_service(
            item,
            ServiceResult(service_name=svc.service_name, input_key="vid42", tech_results=[]),
        )
        assert received["data"] == ("vid42", 10, "time")

    @pytest.mark.asyncio
    async def test_url_fallback_for_video_id(self, svc):
        item = {"url": "https://www.youtube.com/watch?v=abc123", "title": "Test"}
        comments = _sample_comments()
        result = await svc.execute_service(item, _ok_result(comments))
        out = result.tech_results[0].output
        assert out["comments_status"] == "available"

    @pytest.mark.asyncio
    async def test_url_no_v_param_returns_unavailable(self, svc):
        item = {"url": "https://www.youtube.com/channel/UCxxx", "title": "No v param"}
        result = await svc.execute_service(
            item,
            ServiceResult(service_name=svc.service_name, input_key="", tech_results=[]),
        )
        out = result.tech_results[0].output
        assert out["comments_status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_tech_exception_returns_failed(self, svc):
        item = {"id": "vid1"}

        class BoomTech:
            name = "youtube_comments"
            caller_service = None

            async def execute(self, data):
                raise RuntimeError("quota exceeded")

        svc._get_technologies = lambda: [BoomTech()]
        result = await svc.execute_service(
            item,
            ServiceResult(service_name=svc.service_name, input_key="vid1", tech_results=[]),
        )
        out = result.tech_results[0].output
        assert out["comments_status"] == "failed"

    @pytest.mark.asyncio
    async def test_get_technologies_called_when_empty_results(self, svc, monkeypatch):
        item = {"id": "vid1"}
        called = []

        class FakeTech:
            name = "youtube_comments"
            caller_service = None

            async def execute(self, data):
                called.append(data)
                return []

        monkeypatch.setattr(svc, "_get_technologies", lambda: [FakeTech()])
        await svc.execute_service(
            item,
            ServiceResult(service_name=svc.service_name, input_key="vid1", tech_results=[]),
        )
        assert called == [("vid1", 20, "relevance")]

    @pytest.mark.asyncio
    async def test_id_preferred_over_url(self, svc):
        received = {}

        class FakeTech:
            name = "youtube_comments"
            caller_service = None

            async def execute(self, data):
                received["data"] = data
                return []

        svc._get_technologies = lambda: [FakeTech()]
        item = {"id": "directid", "url": "https://www.youtube.com/watch?v=urlid"}
        await svc.execute_service(
            item,
            ServiceResult(service_name=svc.service_name, input_key="directid", tech_results=[]),
        )
        assert received["data"][0] == "directid"
