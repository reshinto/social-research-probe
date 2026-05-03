"""YouTubeNarrationStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeNarrationStage(BaseStage):
    """Read evidence summary aloud via TTS."""

    @property
    def stage_name(self) -> str:
        return "narration"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.reporting.audio import AudioReportService

        if not self._is_enabled(state):
            return state

        narration = str(state.outputs.get("report", {}).get("evidence_summary", ""))
        if narration:
            await AudioReportService().execute_batch([{"text": narration}])
        return state
