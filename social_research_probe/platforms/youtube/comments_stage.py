"""YouTubeCommentsStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.pipeline.helpers import dict_items, first_tech_output


class YouTubeCommentsStage(BaseStage):
    """Fetch YouTube comments for top-N items."""

    @property
    def stage_name(self) -> str:
        return "comments"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.comments import CommentsService

        top_n = list(state.get_stage_output("transcript").get("top_n", []))
        if not self._is_enabled(state):
            self._set_comments_output(state, self._disabled_items(top_n))
            return state
        if not top_n:
            self._set_comments_output(state, top_n)
            return state

        available_items = dict_items(top_n)
        fetch_items = self._fetch_items(available_items, state)
        inputs = self._service_inputs(fetch_items, state)
        results = await CommentsService().execute_batch(inputs)
        enriched = self._enriched_items(fetch_items, results)
        enriched.extend(self._not_attempted_items(available_items, state))
        self._set_comments_output(state, enriched)
        return state

    def _set_comments_output(self, state: PipelineState, top_n: list) -> None:
        state.set_stage_output("comments", {"top_n": top_n})

    def _disabled_items(self, top_n: list) -> list:
        return [
            {**item, "comments_status": "disabled"} if isinstance(item, dict) else item
            for item in top_n
        ]

    def _comments_config(self, state: PipelineState) -> dict:
        cfg = state.platform_config.get("comments", {})
        return cfg if isinstance(cfg, dict) else {}

    def _max_videos(self, state: PipelineState) -> int:
        return int(self._comments_config(state).get("max_videos", 5))

    def _max_comments(self, state: PipelineState) -> int:
        return int(self._comments_config(state).get("max_comments_per_video", 20))

    def _comment_order(self, state: PipelineState) -> str:
        return str(self._comments_config(state).get("order", "relevance"))

    def _fetch_items(self, dict_items: list[dict], state: PipelineState) -> list[dict]:
        return dict_items[: self._max_videos(state)]

    def _service_inputs(self, fetch_items: list[dict], state: PipelineState) -> list[dict]:
        max_comments = self._max_comments(state)
        order = self._comment_order(state)
        return [self._service_input(item, max_comments, order) for item in fetch_items]

    def _service_input(self, item: dict, max_comments: int, order: str) -> dict:
        return {**item, "_max_comments": max_comments, "_order": order}

    def _enriched_items(self, fetch_items: list[dict], results: list) -> list[dict]:
        enriched: list[dict] = []
        for fetch_item, result in zip(fetch_items, results, strict=True):
            enriched.append(self._enriched_item(fetch_item, result))
        return enriched

    def _enriched_item(self, fetch_item: dict, result: object) -> dict:
        merged = self._result_item(result)
        return merged if merged is not None else {**fetch_item, "comments_status": "failed"}

    def _result_item(self, result: object) -> dict | None:
        return first_tech_output(result, dict)

    def _not_attempted_items(self, dict_items: list[dict], state: PipelineState) -> list[dict]:
        return [
            {**item, "comments_status": "not_attempted"}
            for item in dict_items[self._max_videos(state) :]
        ]
