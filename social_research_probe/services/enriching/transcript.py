"""Transcript fetching service: YouTube captions API → yt-dlp → Whisper fallback."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult
from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
    YoutubeTranscriptFetch,
)


class TranscriptService(BaseService):
    """Fetch transcripts for video items: captions API first, Whisper as fallback.

    Input per item: a ScoredItem dict with a "url" key.
    Output: ServiceResult with transcript text in the successful TechResult's output.
    """

    service_name: ClassVar[str] = "youtube.enriching.transcript"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.transcript"

    def _get_technologies(self, cfg):
        return [YoutubeTranscriptFetch()]

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Fetch transcript for one ScoredItem; try captions then Whisper fallback."""
        url = data.get("url", "") if isinstance(data, dict) else str(data)

        # Try YouTube captions API first
        yt_tech = YoutubeTranscriptFetch()
        yt_tech.caller_service = self.service_name
        transcript = None
        tech_results: list[TechResult] = []
        try:
            transcript = await yt_tech.execute(url)
            tech_results.append(TechResult(
                tech_name=yt_tech.name, input=url, output=transcript, success=transcript is not None
            ))
        except Exception as exc:
            tech_results.append(TechResult(
                tech_name=yt_tech.name, input=url, output=None, success=False, error=str(exc)
            ))

        # Whisper fallback if captions unavailable
        if not transcript:
            try:
                import asyncio
                import tempfile

                from social_research_probe.technologies.media_fetch.yt_dlp import download_audio
                from social_research_probe.technologies.transcript_fetch.whisper import (
                    transcribe_audio,
                )

                with tempfile.TemporaryDirectory(prefix="srp-ytdlp-") as tmpdir:
                    audio_path = await asyncio.to_thread(download_audio, url, tmpdir)
                    if audio_path is not None:
                        transcript = await asyncio.to_thread(transcribe_audio, audio_path)
                tech_results.append(TechResult(
                    tech_name="whisper_fallback", input=url, output=transcript, success=transcript is not None
                ))
            except Exception as exc:
                tech_results.append(TechResult(
                    tech_name="whisper_fallback", input=url, output=None, success=False, error=str(exc)
                ))

        return ServiceResult(service_name=self.service_name, input_key=url, tech_results=tech_results)
