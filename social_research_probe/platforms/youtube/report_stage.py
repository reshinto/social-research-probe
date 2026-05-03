"""YouTubeReportStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeReportStage(BaseStage):
    """Write text and HTML research reports to disk.

    Examples:
        Input:
            YouTubeReportStage
        Output:
            YouTubeReportStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `report` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "report"
        """
        return "report"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube report stage and publish its PipelineState output.

        The YouTube report stage reads the state built so far and publishes the smallest output later
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
        from social_research_probe.services.reporting.report import ReportService

        if not self._is_enabled(state):
            return state

        report = state.outputs.get("report", {})
        allow_html = bool(state.platform_config.get("allow_html", True))
        result = (
            await ReportService().execute_batch([{"report": report, "allow_html": allow_html}])
        )[0]
        report_path = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, str)),
            "",
        )
        report["report_path"] = report_path
        state.outputs["report"] = report
        return state
