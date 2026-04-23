"""Whisper-based transcript technology adapter."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.progress import log

# Module-level model cache to avoid reloading Whisper (10-15s overhead).
_MODEL_CACHE: dict[tuple[int, str], object] = {}


def _load_model_cached(whisper_module: object, name: str) -> object:
    """Load and cache a Whisper model by (module_id, name)."""
    key = (id(whisper_module), name)
    cached = _MODEL_CACHE.get(key)
    if cached is None:
        cached = whisper_module.load_model(name)  # type: ignore[attr-defined]
        _MODEL_CACHE[key] = cached
    return cached


def transcribe_audio(audio_path: Path, model_name: str = "base") -> str | None:
    """Transcribe an audio file via Whisper; return text or None."""
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

    Input: Path to audio file.
    Output: {filename: transcript_text} or None on failure.
    """

    name: ClassVar[str] = "whisper"
    health_check_key: ClassVar[str] = "whisper"
    enabled_config_key: ClassVar[str] = "whisper"

    async def _execute(self, data: Path) -> dict:
        """Transcribe audio at data path; return {filename: text}."""
        import asyncio
        text = await asyncio.to_thread(transcribe_audio, data)
        if text is None:
            raise RuntimeError(f"Whisper produced no transcript for: {data}")
        return {data.name: text}
