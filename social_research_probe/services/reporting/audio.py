"""Audio report generation service (TTS; synchronous; runs after all stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult


class AudioReportService(BaseService):
    """Generate audio narration for the research report.

    Synchronous — runs after HTML report is complete.
    Input: dict with 'text' (narration text) key.
    Tries VoiceboxTTS first, falls back to MacTTS if unavailable.
    """

    service_name: ClassVar[str] = "youtube.reporting.audio"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.audio"
    run_technologies_concurrently: ClassVar[bool] = False

    def _get_technologies(self):
        from social_research_probe.technologies.tts.mac_tts import MacTTS
        from social_research_probe.technologies.tts.voicebox import VoiceboxTTS

        return [VoiceboxTTS(), MacTTS()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
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
