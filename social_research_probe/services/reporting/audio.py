"""Audio report generation service (TTS; synchronous; runs after all stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import BaseService, ServiceResult, TechResult


class AudioReportService(BaseService):
    """Generate audio narration for the research report.

    Synchronous — runs after HTML report is complete.
    Input: dict with 'text' (narration text) key.
    Tries VoiceboxTTS first, falls back to MacTTS if unavailable.
    """

    service_name: ClassVar[str] = "youtube.reporting.audio"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.audio"

    def _get_technologies(self, cfg):
        from social_research_probe.technologies.tts.voicebox import VoiceboxTTS

        return [VoiceboxTTS()]

    async def execute_one(self, data: object, *, cfg) -> ServiceResult:
        """Synthesize narration audio; try Voicebox then MacTTS fallback."""
        from social_research_probe.technologies.tts.voicebox import VoiceboxTTS

        text = data.get("text", "") if isinstance(data, dict) else str(data)
        tech = VoiceboxTTS()
        tech.caller_service = self.service_name
        try:
            output = await tech.execute(text)
            tr = TechResult(
                tech_name=tech.name, input=data, output=output, success=output is not None
            )
        except Exception as exc:
            tr = TechResult(
                tech_name=tech.name, input=data, output=None, success=False, error=str(exc)
            )
        return ServiceResult(service_name=self.service_name, input_key="text", tech_results=[tr])
