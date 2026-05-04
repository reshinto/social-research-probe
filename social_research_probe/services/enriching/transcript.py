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

    Examples:
        Input:
            TranscriptService
        Output:
            TranscriptService
    """

    service_name: ClassVar[str] = "youtube.enriching.transcript"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.transcript"
    run_technologies_concurrently: ClassVar[bool] = False

    def _get_technologies(self):
        """Return the technology adapters this service should run.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _get_technologies()
            Output:
                "AI safety"
        """
        return [YoutubeTranscriptFetch(), TranscriptWhisperTech()]

    async def _run_with_fallback(self, url: str) -> list[TechResult]:
        """Try each technology in order, stopping on the first success.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            url: Stable source identifier or URL used to join records across stages and exports.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                await _run_with_fallback(
                    url="https://youtu.be/abc123",
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
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
        """Return enriched item dict with transcript and transcript_status.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            tech_results: Technology result object carrying adapter output and success diagnostics.
            transcript: Source text, prompt text, or raw value being parsed, normalized, classified, or
                        sent to a provider.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _build_item_output(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    tech_results=TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True),
                    transcript="This tool reduces latency by 30%.",
                )
            Output:
                {"enabled": True}
        """
        if transcript:
            return {**data, "transcript": transcript, "transcript_status": "available"}
        if any(tr.error for tr in tech_results):
            return {**data, "transcript_status": "failed"}
        return {**data, "transcript_status": "unavailable"}

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the transcript service result.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_service(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
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
