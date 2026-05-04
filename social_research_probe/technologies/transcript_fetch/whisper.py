"""Whisper-based transcript technology adapter."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.display.progress import log

# Module-level model cache to avoid reloading Whisper (10-15s overhead).
_MODEL_CACHE: dict[tuple[int, str], object] = {}


def _load_model_cached(whisper_module: object, name: str) -> object:
    """Load model cached from disk or active configuration.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        whisper_module: Imported Whisper module or compatible object used for transcription.
        name: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _load_model_cached(
                whisper_module="AI safety",
                name="AI safety",
            )
        Output:
            "AI safety"
    """
    key = (id(whisper_module), name)
    cached = _MODEL_CACHE.get(key)
    if cached is None:
        cached = whisper_module.load_model(name)  # type: ignore[attr-defined]
        _MODEL_CACHE[key] = cached
    return cached


def transcribe_audio(audio_path: Path, model_name: str = "base") -> str | None:
    """Transcribe an audio file via Whisper; return text or None.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        audio_path: Filesystem location used to read, write, or resolve project data.
        model_name: Whisper model name requested for local transcription.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            transcribe_audio(
                audio_path=Path("report.html"),
                model_name="AI safety",
            )
        Output:
            "AI safety"
    """
    try:
        import whisper
    except ImportError:
        return None
    model = _load_model_cached(whisper, model_name)
    log(f"[srp] whisper: transcribing {audio_path.name}")
    result = model.transcribe(str(audio_path), language="en", fp16=False)  # type: ignore[union-attr]
    return (result.get("text") or "").strip() or None


class WhisperTranscript(BaseTechnology[Path, dict]):
    """Transcribe an audio file using OpenAI Whisper.

    Input: Path to audio file. Output: {filename: transcript_text} or None on failure.

    Examples:
        Input:
            WhisperTranscript
        Output:
            WhisperTranscript
    """

    name: ClassVar[str] = "whisper"
    health_check_key: ClassVar[str] = "whisper"
    enabled_config_key: ClassVar[str] = "whisper"

    async def _execute(self, data: Path) -> dict:
        """Transcribe audio at data path; return {filename: text}.

        Fetch adapters hide provider response details and give services the stable source-item shape the
        rest of the project expects.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                {"enabled": True}
        """
        import asyncio

        text = await asyncio.to_thread(transcribe_audio, data)
        if text is None:
            raise RuntimeError(f"Whisper produced no transcript for: {data}")
        return {data.name: text}
