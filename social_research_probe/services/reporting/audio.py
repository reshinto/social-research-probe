"""Audio report generation service (TTS; synchronous; runs after all stages)."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services.base import FallbackService, ServiceResult


class AudioReportService(FallbackService):
    """Generate audio narration for the research report.

    Synchronous — runs after HTML report is complete.
    Input: dict with 'text' (narration text) key.
    Tries VoiceboxTTS first, falls back to MacTTS if unavailable.
    """

    service_name: ClassVar[str] = "youtube.reporting.audio"
    enabled_config_key: ClassVar[str] = "services.youtube.reporting.audio"

    def _get_technologies(self):
        from social_research_probe.technologies.tts.mac_tts import MacTTS
        from social_research_probe.technologies.tts.voicebox import VoiceboxTTS

        return [VoiceboxTTS(), MacTTS()]

    async def execute_one(self, data: object) -> ServiceResult:
        text = data.get("text", "") if isinstance(data, dict) else str(data)
        result = await super().execute_one(text)
        result.input_key = "text"
        return result
