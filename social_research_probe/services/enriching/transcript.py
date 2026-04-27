"""Transcript fetching service: YouTube captions API → yt-dlp → Whisper fallback."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import FallbackService, ServiceResult
from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
    YoutubeTranscriptFetch,
)


class TranscriptWhisperTech(BaseTechnology[str, str]):
    """Fallback technology using yt-dlp to download audio and Whisper to transcribe."""

    name: ClassVar[str] = "whisper_fallback"

    async def _execute(self, input_data: str) -> str | None:
        import asyncio
        import tempfile

        from social_research_probe.technologies.media_fetch.yt_dlp import download_audio
        from social_research_probe.technologies.transcript_fetch.whisper import transcribe_audio

        with tempfile.TemporaryDirectory(prefix="srp-ytdlp-") as tmpdir:
            audio_path = await asyncio.to_thread(download_audio, input_data, tmpdir)
            if audio_path is not None:
                return await asyncio.to_thread(transcribe_audio, audio_path)
        return None


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
