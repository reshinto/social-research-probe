"""Audio report generation service (TTS; synchronous; runs after all stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult


class AudioReportService(BaseService):
    """Generate audio narration for the research report.

    Synchronous — runs after HTML report is complete. Input: dict with 'text' (narration text) key.
    Tries VoiceboxTTS first, falls back to MacTTS if unavailable.

    Examples:
        Input:
            AudioReportService
        Output:
            AudioReportService
    """

    service_name: ClassVar[str] = "youtube.reporting.audio"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.audio"
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
        from social_research_probe.technologies.tts.mac_tts import MacTTS
        from social_research_probe.technologies.tts.voicebox import VoiceboxTTS

        return [VoiceboxTTS(), MacTTS()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the audio report service result.

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
        text = data.get("text", "") if isinstance(data, dict) else str(data)

        tech_results: list[TechResult] = result.tech_results
        if not tech_results:
            for tech in self._get_technologies():
                tech.caller_service = self.service_name
                try:
                    output = await tech.execute(text)
                    tr = TechResult(
                        tech_name=tech.name,
                        input=text,
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
                            input=text,
                            output=None,
                            success=False,
                            error=str(exc),
                        )
                    )

        return ServiceResult(
            service_name=self.service_name,
            input_key="text",
            tech_results=tech_results,
        )
