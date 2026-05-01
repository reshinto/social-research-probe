"""YouTube comment fetching service: enriches items with comment text and metadata."""

from __future__ import annotations

from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from social_research_probe.services import BaseService, ServiceResult, TechResult


def _extract_video_id(item: dict) -> str | None:
    """Return YouTube video ID from item dict.

    Prefers item["id"] when it looks like a bare video ID (no slashes/dots),
    then falls back to parsing the ``v`` query parameter from ``item["url"]``.
    """
    raw_id = item.get("id")
    if isinstance(raw_id, str) and raw_id and "/" not in raw_id and "." not in raw_id:
        return raw_id
    url = item.get("url")
    if isinstance(url, str):
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        v = qs.get("v", [None])[0]
        if v:
            return v
    return None


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

        video_id = _extract_video_id(data)
        max_results = int(data.get("_max_comments", 20))
        order = str(data.get("_order", "relevance"))

        if not video_id:
            merged = {**data, "source_comments": [], "comments": [], "comments_status": "unavailable"}
            result.tech_results = [
                TechResult(
                    tech_name="youtube_comments",
                    input="",
                    output=merged,
                    success=False,
                )
            ]
            return result

        tech_results = result.tech_results
        if not tech_results:
            tech = self._get_technologies()[0]
            tech.caller_service = self.service_name
            try:
                output = await tech.execute((video_id, max_results, order))
                tech_results.append(
                    TechResult(
                        tech_name=tech.name,
                        input=video_id,
                        output=output,
                        success=output is not None,
                    )
                )
            except Exception as exc:
                tech_results.append(
                    TechResult(
                        tech_name="youtube_comments",
                        input=video_id,
                        output=None,
                        success=False,
                        error=str(exc),
                    )
                )

        first = tech_results[0]
        raw_comments = first.output if first.success else None

        if raw_comments:
            merged = {
                **data,
                "source_comments": raw_comments,
                "comments": [c.get("text", "") for c in raw_comments if isinstance(c, dict)],
                "comments_status": "available",
            }
            tech_results[0] = TechResult(
                tech_name=first.tech_name,
                input=video_id,
                output=merged,
                success=True,
            )
        elif raw_comments is not None:
            merged = {**data, "source_comments": [], "comments": [], "comments_status": "unavailable"}
            tech_results[0] = TechResult(
                tech_name=first.tech_name,
                input=video_id,
                output=merged,
                success=False,
            )
        else:
            merged = {**data, "source_comments": [], "comments": [], "comments_status": "failed"}
            tech_results[0] = TechResult(
                tech_name=first.tech_name,
                input=video_id,
                output=merged,
                success=False,
            )

        return ServiceResult(
            service_name=self.service_name,
            input_key=video_id,
            tech_results=tech_results,
        )
