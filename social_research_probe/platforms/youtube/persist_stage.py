"""YouTubePersistStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubePersistStage(BaseStage):
    """Persist the completed research run to the local SQLite database.

    Examples:
        Input:
            YouTubePersistStage
        Output:
            YouTubePersistStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `persist` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "persist"
        """
        return "persist"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube persist stage and publish its PipelineState output.

        The YouTube persist stage reads the state built so far and publishes the smallest output later
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
        if not self._is_enabled(state):
            return state
        report = state.outputs.get("report") or {}
        if not report:
            return state
        from social_research_probe.config import load_active_config
        from social_research_probe.services.persistence import PersistenceService

        cfg = load_active_config()
        db_cfg = cfg.raw.get("database") or {}
        if not db_cfg.get("enabled", True):
            return state
        payload = {
            "report": report,
            "db_path": cfg.database_path,
            "config": cfg.raw,
            "persist_transcript_text": db_cfg.get("persist_transcript_text", False),
            "persist_comment_text": db_cfg.get("persist_comment_text", True),
        }
        results = await PersistenceService().execute_batch([payload])
        for r in results:
            for tr in r.tech_results:
                if not tr.success:
                    report.setdefault("warnings", []).append(
                        f"persistence: {tr.error or 'sqlite persist failed'}"
                    )
                elif isinstance(tr.output, dict):
                    state.set_stage_output(
                        "persist",
                        {
                            "db_path": tr.output.get("db_path"),
                            "run_id": tr.output.get("run_id"),
                        },
                    )
        state.outputs["report"] = report
        return state
