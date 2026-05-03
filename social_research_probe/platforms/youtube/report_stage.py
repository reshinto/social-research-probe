"""YouTubeReportStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeReportStage(BaseStage):
    """Write text and HTML research reports to disk."""

    @property
    def stage_name(self) -> str:
        return "report"

    async def execute(self, state: PipelineState) -> PipelineState:
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
