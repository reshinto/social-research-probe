"""YouTubeCommentsStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.pipeline.helpers import dict_items, first_tech_output


class YouTubeCommentsStage(BaseStage):
    """Fetch YouTube comments for top-N items.

    Examples:
        Input:
            YouTubeCommentsStage
        Output:
            YouTubeCommentsStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `comments` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "comments"
        """
        return "comments"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube comments stage and publish its PipelineState output.

        The YouTube comments stage reads the state built so far and publishes the smallest output later
        stages need.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            The same PipelineState instance after this stage has published its output.

        Examples:
            Input:
                await execute(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                PipelineState(platform_type="youtube", cmd=None, cache=None)
        """
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
        """Store top_n where later pipeline code expects to find it.

        Later stages should not care whether comments were fetched, unavailable, or skipped; they just
        read the same fields.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.
            top_n: Ordered source items being carried through the current pipeline step.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                _set_comments_output(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                    top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                None
        """
        state.set_stage_output("comments", {"top_n": top_n})

    def _disabled_items(self, top_n: list) -> list:
        """Return an item with the comment fields expected by later enrichment and reports.

        The YouTube pipeline shares one PipelineState object; this helper documents the part of that
        state this stage reads or writes.

        Args:
            top_n: Ordered source items being carried through the current pipeline step.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _disabled_items(
                    top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                [{"title": "Example", "comments_status": "disabled"}]
        """
        return [
            {**item, "comments_status": "disabled"} if isinstance(item, dict) else item
            for item in top_n
        ]

    def _comments_config(self, state: PipelineState) -> dict:
        """Read the comments configuration block for the current YouTube run.

        Downstream stages can read the same fields regardless of which source text was available.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _comments_config(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                {"max_videos": 5, "max_comments_per_video": 20, "order": "relevance"}
        """
        cfg = state.platform_config.get("comments", {})
        return cfg if isinstance(cfg, dict) else {}

    def _max_videos(self, state: PipelineState) -> int:
        """Read the configured limit for how many videos should fetch comments.

        The YouTube pipeline shares one PipelineState object; this helper documents the part of that
        state this stage reads or writes.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Integer count, limit, status code, or timeout used by the caller.

        Examples:
            Input:
                _max_videos(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                5
        """
        return int(self._comments_config(state).get("max_videos", 5))

    def _max_comments(self, state: PipelineState) -> int:
        """Read the configured per-video comment limit.

        Downstream stages can read the same fields regardless of which source text was available.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Integer count, limit, status code, or timeout used by the caller.

        Examples:
            Input:
                _max_comments(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                20
        """
        return int(self._comments_config(state).get("max_comments_per_video", 20))

    def _comment_order(self, state: PipelineState) -> str:
        """Read the configured YouTube comment ordering mode.

        Downstream stages can read the same fields regardless of which source text was available.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Examples:
            Input:
                _comment_order(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                "relevance"
        """
        return str(self._comments_config(state).get("order", "relevance"))

    def _fetch_items(self, dict_items: list[dict], state: PipelineState) -> list[dict]:
        """Fetch items without exposing provider details to callers.

        The YouTube pipeline shares one PipelineState object; this helper documents the part of that
        state this stage reads or writes.

        Args:
            dict_items: Ordered source items being carried through the current pipeline step.
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _fetch_items(
                    dict_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        return dict_items[: self._max_videos(state)]

    def _service_inputs(self, fetch_items: list[dict], state: PipelineState) -> list[dict]:
        """Build the comment service payloads for the videos selected for comment fetching.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            fetch_items: Ordered source items being carried through the current pipeline step.
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _service_inputs(
                    fetch_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        max_comments = self._max_comments(state)
        order = self._comment_order(state)
        return [self._service_input(item, max_comments, order) for item in fetch_items]

    def _service_input(self, item: dict, max_comments: int, order: str) -> dict:
        """Attach comment-fetch request fields before handing an item to CommentsService.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            item: Single source item, database row, or registry entry being transformed.
            max_comments: Count, database id, index, or limit that bounds the work being performed.
            order: Provider ordering mode, such as relevance or time.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _service_input(
                    item={"title": "Example", "url": "https://youtu.be/demo"},
                    max_comments=3,
                    order="relevance",
                )
            Output:
                {"title": "Example", "_max_comments": 20, "_order": "relevance"}
        """
        return {**item, "_max_comments": max_comments, "_order": order}

    def _enriched_items(self, fetch_items: list[dict], results: list) -> list[dict]:
        """Merge fetched comments back into the original ranked items.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            fetch_items: Ordered source items being carried through the current pipeline step.
            results: Service or technology result being inspected for payload and diagnostics.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _enriched_items(
                    fetch_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    results=[ServiceResult(service_name="comments", input_key="demo", tech_results=[])],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        enriched: list[dict] = []
        for fetch_item, result in zip(fetch_items, results, strict=True):
            enriched.append(self._enriched_item(fetch_item, result))
        return enriched

    def _enriched_item(self, fetch_item: dict, result: object) -> dict:
        """Return an item with the comment fields expected by later enrichment and reports.

        The YouTube pipeline shares one PipelineState object; this helper documents the part of that
        state this stage reads or writes.

        Args:
            fetch_item: Single source item, database row, or registry entry being transformed.
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _enriched_item(
                    fetch_item={"title": "Example", "url": "https://youtu.be/demo"},
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                {"enabled": True}
        """
        merged = self._result_item(result)
        return merged if merged is not None else {**fetch_item, "comments_status": "failed"}

    def _result_item(self, result: object) -> dict | None:
        """Extract the first successful payload from a ServiceResult.

        This keeps ServiceResult parsing out of stages, where missing and failed outputs should look the
        same.

        Args:
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _result_item(
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                {"enabled": True}
        """
        return first_tech_output(result, dict)

    def _not_attempted_items(self, dict_items: list[dict], state: PipelineState) -> list[dict]:
        """Return an item with the comment fields expected by later enrichment and reports.

        The YouTube pipeline shares one PipelineState object; this helper documents the part of that
        state this stage reads or writes.

        Args:
            dict_items: Ordered source items being carried through the current pipeline step.
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _not_attempted_items(
                    dict_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        return [
            {**item, "comments_status": "not_attempted"}
            for item in dict_items[self._max_videos(state) :]
        ]
