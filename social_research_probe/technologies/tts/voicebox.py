"""Voicebox helpers for pre-rendering report narration audio."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.secrets import read_runtime_secret

_DEFAULT_TIMEOUT_SECONDS = 300


def synthesize(
    text: str,
    *,
    api_base: str,
    profile_id: str,
    language: str = "en",
    max_chunk_chars: int = 400,
    crossfade_ms: int = 50,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bytes, str]:
    """Return Voicebox audio bytes plus the response content type."""
    payload = json.dumps(
        {
            "profile_id": profile_id,
            "text": text,
            "language": language,
            "max_chunk_chars": max_chunk_chars,
            "crossfade_ms": crossfade_ms,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/generate/stream",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "audio/*"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            audio = resp.read()
            content_type = resp.headers.get("Content-Type", "audio/wav")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Voicebox returned {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Voicebox unreachable: {exc.reason}") from exc

    if not audio:
        raise RuntimeError("Voicebox returned empty audio")
    return audio, content_type


def write_audio(
    text: str,
    *,
    out_base: Path,
    api_base: str,
    profile_id: str,
    language: str = "en",
    max_chunk_chars: int = 400,
    crossfade_ms: int = 50,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> Path:
    """Synthesize *text* with Voicebox and write a companion audio file."""
    audio, content_type = synthesize(
        text,
        api_base=api_base,
        profile_id=profile_id,
        language=language,
        max_chunk_chars=max_chunk_chars,
        crossfade_ms=crossfade_ms,
        timeout_seconds=timeout_seconds,
    )
    ext = _extension_for_content_type(content_type)
    out_path = out_base.parent / f"{out_base.name}{ext}"
    out_path.write_bytes(audio)
    return out_path


def _extension_for_content_type(content_type: str) -> str:
    """Map a response content type to a file extension."""
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized == "audio/mpeg":
        return ".mp3"
    if normalized == "audio/wav" or normalized == "audio/x-wav":
        return ".wav"
    if normalized == "audio/ogg":
        return ".ogg"
    return ".bin"


def _get_server_url() -> str:
    """Return Voicebox server URL from secrets.toml, falling back to config default."""
    url = read_runtime_secret("tts_voicebox_server_url")
    if url:
        return url
    from social_research_probe.config import load_active_config

    return load_active_config().voicebox["api_base"]


def _get_default_profile() -> str:
    """Return default Voicebox profile name from secrets.toml."""
    return read_runtime_secret("tts_voicebox_default_profile") or "Jarvis"


class VoiceboxTTS(BaseTechnology[str, dict]):
    """Synthesize text to audio via a local Voicebox server.

    Input: text string.
    Output: {"audio_path": Path, "profile": str} or None on failure.
    """

    name: ClassVar[str] = "voicebox_tts"
    health_check_key: ClassVar[str] = "voicebox_tts"
    enabled_config_key: ClassVar[str] = "voicebox"

    async def _execute(self, data: str) -> dict:
        """Synthesize data (text) and return audio path dict."""
        import asyncio
        import tempfile
        from pathlib import Path as _Path

        server_url = _get_server_url()
        profile_id = _get_default_profile()
        out_base = _Path(tempfile.mkdtemp(prefix="srp-tts-")) / "audio"

        def _synth() -> _Path:
            return write_audio(
                data,
                out_base=out_base,
                api_base=server_url,
                profile_id=profile_id,
            )

        audio_path = await asyncio.to_thread(_synth)
        return {"audio_path": audio_path, "profile": profile_id}
