"""YouTubeExportStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeExportStage(BaseStage):
    """Write export artifacts (CSV, markdown, JSON) alongside the HTML report.

    Examples:
        Input:
            YouTubeExportStage
        Output:
            YouTubeExportStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `export` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "export"
        """
        return "export"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube export stage and publish its PipelineState output.

        The YouTube export stage reads the state built so far and publishes the smallest output later
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
        from social_research_probe.services.reporting.export import ExportService
        from social_research_probe.utils.pipeline.helpers import resolve_html_report_path

        if not self._is_enabled(state):
            return state

        report = state.outputs.get("report", {})
        html_path = resolve_html_report_path(report)
        if html_path is None:
            return state

        stem = html_path.stem
        reports_dir = html_path.parent
        result = (
            await ExportService().execute_batch(
                [
                    {
                        "report": report,
                        "config": state.platform_config,
                        "stem": stem,
                        "reports_dir": reports_dir,
                    }
                ]
            )
        )[0]
        export_paths = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, dict)),
            {},
        )
        report["export_paths"] = export_paths
        state.outputs["report"] = report
        state.set_stage_output("export", {"export_paths": export_paths})
        return state
