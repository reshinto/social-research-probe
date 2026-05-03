"""YouTube platform package."""

from __future__ import annotations

import asyncio

from social_research_probe.platforms import BaseResearchPlatform, BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.display.progress import log_with_time

from .assemble_stage import YouTubeAssembleStage
from .charts_stage import YouTubeChartsStage
from .claims_stage import YouTubeClaimsStage
from .classify_stage import YouTubeClassifyStage
from .comments_stage import YouTubeCommentsStage
from .corroborate_stage import YouTubeCorroborateStage
from .export_stage import YouTubeExportStage
from .fetch_stage import YouTubeFetchStage
from .narration_stage import YouTubeNarrationStage
from .persist_stage import YouTubePersistStage
from .report_stage import YouTubeReportStage
from .score_stage import YouTubeScoreStage
from .stats_stage import YouTubeStatsStage
from .structured_synthesis_stage import YouTubeStructuredSynthesisStage
from .summary_stage import YouTubeSummaryStage
from .synthesis_stage import YouTubeSynthesisStage
from .transcript_stage import YouTubeTranscriptStage


class YouTubePipeline(BaseResearchPlatform):
    """Orchestrates all YouTube research stages and post-stage reports."""

    def stages(self) -> list[list[BaseStage]]:
        return [
            [YouTubeFetchStage()],
            [YouTubeClassifyStage()],
            [YouTubeScoreStage()],
            [YouTubeTranscriptStage(), YouTubeStatsStage(), YouTubeChartsStage()],
            [YouTubeCommentsStage()],
            [YouTubeSummaryStage()],
            [YouTubeClaimsStage()],
            [YouTubeCorroborateStage()],
            [YouTubeSynthesisStage()],
            [YouTubeAssembleStage()],
            [YouTubeStructuredSynthesisStage()],
            [YouTubeReportStage(), YouTubeNarrationStage()],
            [YouTubeExportStage()],
            [YouTubePersistStage()],
        ]

    @log_with_time("[srp] youtube/pipeline: run")
    async def run(self, state: PipelineState) -> PipelineState:
        for group in self.stages():
            if len(group) == 1:
                state = await group[0].run(state)
            else:
                await asyncio.gather(*(s.run(state) for s in group))
        return state


__all__ = [
    "YouTubeAssembleStage",
    "YouTubeChartsStage",
    "YouTubeClaimsStage",
    "YouTubeClassifyStage",
    "YouTubeCommentsStage",
    "YouTubeCorroborateStage",
    "YouTubeExportStage",
    "YouTubeFetchStage",
    "YouTubeNarrationStage",
    "YouTubePersistStage",
    "YouTubePipeline",
    "YouTubeReportStage",
    "YouTubeScoreStage",
    "YouTubeStatsStage",
    "YouTubeStructuredSynthesisStage",
    "YouTubeSummaryStage",
    "YouTubeSynthesisStage",
    "YouTubeTranscriptStage",
]
