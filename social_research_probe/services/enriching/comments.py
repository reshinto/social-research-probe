"""YouTube comment fetching service: enriches items with comment text and metadata."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.utils.core.youtube import youtube_video_id_from_item


def _empty_comments_item(data: dict, status: str) -> dict:
    """Return an item with the comment fields expected by later enrichment and reports.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        status: Lifecycle, evidence, or provider status being written into the output record.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _empty_comments_item(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                status="available",
            )
        Output:
            {"enabled": True}
    """
    return {**data, "source_comments": [], "comments": [], "comments_status": status}


def _comment_texts(raw_comments: list) -> list[str]:
    """Extract plain text strings from raw YouTube comment dictionaries.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        raw_comments: Comment records or text used as audience evidence.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _comment_texts(
                raw_comments=[{"text": "Useful point"}],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    return [c.get("text", "") for c in raw_comments if isinstance(c, dict)]


def _available_comments_item(data: dict, raw_comments: list) -> dict:
    """Return an item with the comment fields expected by later enrichment and reports.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        raw_comments: Comment records or text used as audience evidence.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _available_comments_item(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                raw_comments=[{"text": "Useful point"}],
            )
        Output:
            {"enabled": True}
    """
    return {
        **data,
        "source_comments": raw_comments,
        "comments": _comment_texts(raw_comments),
        "comments_status": "available",
    }


def _status_for_comments(raw_comments: object) -> str:
    """Translate a comments adapter response into `available`, `unavailable`, or `failed`.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        raw_comments: Comment records or text used as audience evidence.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _status_for_comments(
                raw_comments=[{"text": "Useful point"}],
            )
        Output:
            "AI safety"
    """
    if raw_comments:
        return "available"
    if raw_comments is not None:
        return "unavailable"
    return "failed"


def _item_for_comments(data: dict, raw_comments: object) -> dict:
    """Attach a consistent comments shape to an item, even when fetching failed.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        raw_comments: Comment records or text used as audience evidence.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _item_for_comments(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                raw_comments=[{"text": "Useful point"}],
            )
        Output:
            {"enabled": True}
    """
    status = _status_for_comments(raw_comments)
    if status == "available" and isinstance(raw_comments, list):
        return _available_comments_item(data, raw_comments)
    return _empty_comments_item(data, status)


class CommentsService(BaseService):
    """Fetch YouTube comments for a video item and enrich with flat + structured data.

    Examples:
        Input:
            CommentsService
        Output:
            CommentsService
    """

    service_name: ClassVar[str] = "youtube.enriching.comments"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.comments"
    run_technologies_concurrently: ClassVar[bool] = False

    def _get_technologies(self):
        """Return the technology adapters this service should run.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _get_technologies()
            Output:
                "AI safety"
        """
        from social_research_probe.technologies.media_fetch import YouTubeCommentsTech

        return [YouTubeCommentsTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the comments service result.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_service(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
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
        """Return a failed comment-fetch result when an item has no usable YouTube video ID.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                _missing_video_result(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
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
        """Reuse existing comment results when possible and fetch comments only when needed.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.
            existing: Intermediate collection used to preserve ordering while stage results are merged.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                await _tech_results(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    video_id="abc123",
                    existing=[],
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
        if existing:
            return existing
        return [await self._fetch_comments(data, video_id)]

    async def _fetch_comments(self, data: dict, video_id: str) -> TechResult:
        """Fetch comments without exposing provider details to callers.

        Later stages should not care whether comments were fetched, unavailable, or skipped; they just
        read the same fields.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                await _fetch_comments(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    video_id="abc123",
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
        tech = self._comments_technology()
        tech.caller_service = self.service_name
        try:
            output = await tech.execute(self._comments_request(data, video_id))
            return self._fetch_success(tech.name, video_id, output)
        except Exception as exc:
            return self._fetch_failure(video_id, exc)

    def _comments_technology(self) -> object:
        """Return the comments adapter selected for this service.

        Downstream stages can read the same fields regardless of which source text was available.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _comments_technology()
            Output:
                "AI safety"
        """
        return self._get_technologies()[0]

    def _comments_request(self, data: dict, video_id: str) -> tuple[str, int, str]:
        """Build the video ID, limit, and ordering tuple for the comments adapter.

        Downstream stages can read the same fields regardless of which source text was available.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.

        Returns:
            Tuple whose positions are part of the public helper contract shown in the example.

        Examples:
            Input:
                _comments_request(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    video_id="abc123",
                )
            Output:
                ("AI safety", "Find unmet needs")
        """
        return (
            video_id,
            int(data.get("_max_comments", 20)),
            str(data.get("_order", "relevance")),
        )

    def _fetch_success(self, tech_name: str, video_id: str, output: object) -> TechResult:
        """Fetch success without exposing provider details to callers.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            tech_name: Technology adapter name stored in diagnostics.
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.
            output: Adapter or helper output being wrapped into the project result shape.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                _fetch_success(
                    tech_name="AI safety",
                    video_id="abc123",
                    output={"comments_status": "available"},
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
        return TechResult(
            tech_name=tech_name,
            input=video_id,
            output=output,
            success=output is not None,
        )

    def _fetch_failure(self, video_id: str, exc: Exception) -> TechResult:
        """Fetch failure without exposing provider details to callers.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.
            exc: Exception whose message should be preserved for diagnostics.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                _fetch_failure(
                    video_id="abc123",
                    exc=RuntimeError("provider failed"),
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
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
        """Replace the first successful comment result with the merged item payload.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.
            tech_results: Technology result object carrying adapter output and success diagnostics.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                _replace_first_result(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    video_id="abc123",
                    tech_results=TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True),
                )
            Output:
                None
        """
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
        """Create the comment-enriched item payload stored on a successful TechResult.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            tech_name: Technology adapter name stored in diagnostics.
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.
            data: Input payload at this service, technology, or pipeline boundary.
            raw_comments: Comment records or text used as audience evidence.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                _merged_result(
                    tech_name="AI safety",
                    video_id="abc123",
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    raw_comments=[{"text": "Useful point"}],
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
        status = _status_for_comments(raw_comments)
        return TechResult(
            tech_name=tech_name,
            input=video_id,
            output=_item_for_comments(data, raw_comments),
            success=status == "available",
        )

    def _service_result(self, video_id: str, tech_results: list[TechResult]) -> ServiceResult:
        """Build the final ServiceResult returned by the comments service.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                      fetched.
            tech_results: Technology result object carrying adapter output and success diagnostics.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                _service_result(
                    video_id="abc123",
                    tech_results=TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True),
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
        return ServiceResult(
            service_name=self.service_name,
            input_key=video_id,
            tech_results=tech_results,
        )
