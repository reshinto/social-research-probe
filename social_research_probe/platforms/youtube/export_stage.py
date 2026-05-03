"""YouTubeExportStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeExportStage(BaseStage):
    """Write export artifacts (CSV, markdown, JSON) alongside the HTML report."""

    @property
    def stage_name(self) -> str:
        return "export"

    async def execute(self, state: PipelineState) -> PipelineState:
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
