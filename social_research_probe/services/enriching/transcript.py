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

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        # Extract the URL since BaseService expects it as TInput
        # for our tech execution.
        url = data.get("url", "") if isinstance(data, dict) else str(data)

        tech_results: list[TechResult] = result.tech_results
        if not tech_results:
            for tech in self._get_technologies():
                tech.caller_service = self.service_name
                try:
                    output = await tech.execute(url)
                    tr = TechResult(
                        tech_name=tech.name,
                        input=url,
                        output=output,
                        success=output is not None,
                    )
                    tech_results.append(tr)
                    if tr.success:
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

        transcript = next(
            (tr.output for tr in tech_results if tr.success and tr.output),
            None,
        )

        if isinstance(data, dict):
            # Attach an explicit status for every attempted item so later stages can
            # separate usable transcripts from unavailable or failed transcript evidence.
            if transcript:
                output = {**data, "transcript": transcript, "transcript_status": "available"}
            elif any(tr.error for tr in tech_results):
                output = {**data, "transcript_status": "failed"}
            else:
                output = {**data, "transcript_status": "unavailable"}

            # The BaseService doesn't run technologies if run_technologies_concurrently is False,
            # so we modify our first successful result or the last failure to carry the output.
            if tech_results:
                tech_results[0].output = output
                tech_results[0].success = bool(transcript)

        return ServiceResult(
            service_name=self.service_name,
            input_key=url,
            tech_results=tech_results,
        )
