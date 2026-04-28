"""Transcript fetching service: YouTube captions API → yt-dlp → Whisper fallback."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import FallbackService, ServiceResult
from social_research_probe.technologies.enriching import TranscriptWhisperTech
from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
    YoutubeTranscriptFetch,
)


class TranscriptService(FallbackService):
    """Fetch transcripts for video items: captions API first, Whisper as fallback.

    Input per item: a string URL or dict with "url" key.
    """

    service_name: ClassVar[str] = "youtube.enriching.transcript"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.transcript"

    def _get_technologies(self):
        return [YoutubeTranscriptFetch(), TranscriptWhisperTech()]

    async def execute_one(self, data: object) -> ServiceResult:
        # Extract the URL since BaseService/FallbackService expects it as TInput
        # for our tech execution.
        url = data.get("url", "") if isinstance(data, dict) else str(data)

        # We need to manually set the input_key on the ServiceResult after running
        # because the original data could be a dict, but we're passing `url` to tech.
        result = await super().execute_one(url)
        return ServiceResult(
            service_name=self.service_name, input_key=url, tech_results=result.tech_results
        )
