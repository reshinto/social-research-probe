"""Transcript fetching service: YouTube captions API → yt-dlp → Whisper fallback."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.technologies.enriching import TranscriptWhisperTech
from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
    YoutubeTranscriptFetch,
)


class TranscriptService(BaseService):
    """Fetch transcripts for video items: captions API first, Whisper as fallback.

    Input per item: a string URL or dict with "url" key.
    """

    service_name: ClassVar[str] = "youtube.enriching.transcript"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.transcript"
    run_technologies_concurrently: ClassVar[bool] = False

    def _get_technologies(self):
        return [YoutubeTranscriptFetch(), TranscriptWhisperTech()]

    async def _run_with_fallback(self, url: str) -> list[TechResult]:
        """Try each technology in order, stopping on the first success."""
        tech_results: list[TechResult] = []
        for tech in self._get_technologies():
            tech.caller_service = self.service_name
            try:
                output = await tech.execute(url)
                tech_results.append(
                    TechResult(
                        tech_name=tech.name,
                        input=url,
                        output=output,
                        success=output is not None,
                    )
                )
                if output is not None:
                    break
            except Exception as exc:
                tech_results.append(
                    TechResult(
                        tech_name=tech.name,
                        input=url,
                        output=None,
                        success=False,
                        error=str(exc),
                    )
                )
        return tech_results

    def _build_item_output(
        self, data: dict, tech_results: list[TechResult], transcript: object
    ) -> dict:
        """Return enriched item dict with transcript and transcript_status."""
        if transcript:
            return {**data, "transcript": transcript, "transcript_status": "available"}
        if any(tr.error for tr in tech_results):
            return {**data, "transcript_status": "failed"}
        return {**data, "transcript_status": "unavailable"}

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        url = data.get("url", "") if isinstance(data, dict) else str(data)
        tech_results: list[TechResult] = result.tech_results
        if not tech_results:
            tech_results = await self._run_with_fallback(url)
        transcript = next((tr.output for tr in tech_results if tr.success and tr.output), None)
        if isinstance(data, dict):
            output = self._build_item_output(data, tech_results, transcript)
            if tech_results:
                tech_results[0].output = output
                tech_results[0].success = bool(transcript)
        return ServiceResult(
            service_name=self.service_name, input_key=url, tech_results=tech_results
        )
