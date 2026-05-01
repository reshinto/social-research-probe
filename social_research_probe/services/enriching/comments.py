"""YouTube comment fetching service: enriches items with comment text and metadata."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.utils.core.youtube import youtube_video_id_from_item


def _empty_comments_item(data: dict, status: str) -> dict:
    return {**data, "source_comments": [], "comments": [], "comments_status": status}


def _comment_texts(raw_comments: list) -> list[str]:
    return [c.get("text", "") for c in raw_comments if isinstance(c, dict)]


def _available_comments_item(data: dict, raw_comments: list) -> dict:
    return {
        **data,
        "source_comments": raw_comments,
        "comments": _comment_texts(raw_comments),
        "comments_status": "available",
    }


def _status_for_comments(raw_comments: object) -> str:
    if raw_comments:
        return "available"
    if raw_comments is not None:
        return "unavailable"
    return "failed"


def _item_for_comments(data: dict, raw_comments: object) -> dict:
    status = _status_for_comments(raw_comments)
    if status == "available" and isinstance(raw_comments, list):
        return _available_comments_item(data, raw_comments)
    return _empty_comments_item(data, status)


class CommentsService(BaseService):
    """Fetch YouTube comments for a video item and enrich with flat + structured data."""

    service_name: ClassVar[str] = "youtube.enriching.comments"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.comments"
    run_technologies_concurrently: ClassVar[bool] = False

    def _get_technologies(self):
        from social_research_probe.technologies.media_fetch import YouTubeCommentsTech

        return [YouTubeCommentsTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        if not isinstance(data, dict):
            return result

        video_id = youtube_video_id_from_item(data)
        if not video_id:
            result.tech_results = [self._missing_video_result(data)]
            return result

        tech_results = await self._tech_results(data, video_id, result.tech_results)
        self._replace_first_result(data, video_id, tech_results)
        return self._service_result(video_id, tech_results)

    def _missing_video_result(self, data: dict) -> TechResult:
        return TechResult(
            tech_name="youtube_comments",
            input="",
            output=_empty_comments_item(data, "unavailable"),
            success=False,
        )

    async def _tech_results(
        self,
        data: dict,
        video_id: str,
        existing: list[TechResult],
    ) -> list[TechResult]:
        if existing:
            return existing
        return [await self._fetch_comments(data, video_id)]

    async def _fetch_comments(self, data: dict, video_id: str) -> TechResult:
        tech = self._comments_technology()
        tech.caller_service = self.service_name
        try:
            output = await tech.execute(self._comments_request(data, video_id))
            return self._fetch_success(tech.name, video_id, output)
        except Exception as exc:
            return self._fetch_failure(video_id, exc)

    def _comments_technology(self) -> object:
        return self._get_technologies()[0]

    def _comments_request(self, data: dict, video_id: str) -> tuple[str, int, str]:
        return (
            video_id,
            int(data.get("_max_comments", 20)),
            str(data.get("_order", "relevance")),
        )

    def _fetch_success(self, tech_name: str, video_id: str, output: object) -> TechResult:
        return TechResult(
            tech_name=tech_name,
            input=video_id,
            output=output,
            success=output is not None,
        )

    def _fetch_failure(self, video_id: str, exc: Exception) -> TechResult:
        return TechResult(
            tech_name="youtube_comments",
            input=video_id,
            output=None,
            success=False,
            error=str(exc),
        )

    def _replace_first_result(
        self,
        data: dict,
        video_id: str,
        tech_results: list[TechResult],
    ) -> None:
        first = tech_results[0]
        raw_comments = first.output if first.success else None
        tech_results[0] = self._merged_result(first.tech_name, video_id, data, raw_comments)

    def _merged_result(
        self,
        tech_name: str,
        video_id: str,
        data: dict,
        raw_comments: object,
    ) -> TechResult:
        status = _status_for_comments(raw_comments)
        return TechResult(
            tech_name=tech_name,
            input=video_id,
            output=_item_for_comments(data, raw_comments),
            success=status == "available",
        )

    def _service_result(self, video_id: str, tech_results: list[TechResult]) -> ServiceResult:
        return ServiceResult(
            service_name=self.service_name,
            input_key=video_id,
            tech_results=tech_results,
        )
