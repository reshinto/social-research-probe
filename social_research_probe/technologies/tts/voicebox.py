"""Voicebox helpers for pre-rendering report narration audio."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
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
    """Return Voicebox audio bytes plus the response content type.

    Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
    command code.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        api_base: Voicebox or provider API base URL used for outbound requests.
        profile_id: Voice or runner profile selected for the current operation.
        language: Language code requested for speech synthesis.
        max_chunk_chars: Count, database id, index, or limit that bounds the work being performed.
        crossfade_ms: Count, database id, index, or limit that bounds the work being performed.
        timeout_seconds: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            synthesize(
                text="This tool reduces latency by 30%.",
                api_base="http://127.0.0.1:5050",
                profile_id={"name": "Alloy", "id": "alloy"},
                language="AI safety",
                max_chunk_chars=3,
                crossfade_ms=3,
                timeout_seconds=3,
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
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
    """Synthesize *text* with Voicebox and write a companion audio file.

    Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
    command code.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        out_base: Output path base used before the audio extension is added.
        api_base: Voicebox or provider API base URL used for outbound requests.
        profile_id: Voice or runner profile selected for the current operation.
        language: Language code requested for speech synthesis.
        max_chunk_chars: Count, database id, index, or limit that bounds the work being performed.
        crossfade_ms: Count, database id, index, or limit that bounds the work being performed.
        timeout_seconds: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            write_audio(
                text="This tool reduces latency by 30%.",
                out_base="AI safety",
                api_base="http://127.0.0.1:5050",
                profile_id={"name": "Alloy", "id": "alloy"},
                language="AI safety",
                max_chunk_chars=3,
                crossfade_ms=3,
                timeout_seconds=3,
            )
        Output:
            None
    """
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
    """Map a response content type to a file extension.

    Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
    command code.

    Args:
        content_type: HTTP content type returned by the Voicebox server.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _extension_for_content_type(
                content_type="AI safety",
            )
        Output:
            "AI safety"
    """
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized == "audio/mpeg":
        return ".mp3"
    if normalized == "audio/wav" or normalized == "audio/x-wav":
        return ".wav"
    if normalized == "audio/ogg":
        return ".ogg"
    return ".bin"


def _get_server_url() -> str:
    """Return Voicebox server URL from secrets.toml, falling back to config default.

    Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
    command code.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _get_server_url()
        Output:
            "http://127.0.0.1:5050"
    """
    url = read_runtime_secret("tts_voicebox_server_url")
    if url:
        return url
    from social_research_probe.config import load_active_config

    return load_active_config().voicebox["api_base"]


def _get_default_profile() -> str:
    """Return default Voicebox profile name from secrets.toml.

    Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
    command code.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _get_default_profile()
        Output:
            "AI safety"
    """
    return read_runtime_secret("tts_voicebox_default_profile") or "Jarvis"


class VoiceboxTTS(BaseTechnology[str, dict]):
    """Synthesize text to audio via a local Voicebox server.

    Input: text string. Output: {"audio_path": Path, "profile": str} or None on failure.

    Examples:
        Input:
            VoiceboxTTS
        Output:
            VoiceboxTTS
    """

    name: ClassVar[str] = "voicebox_tts"
    health_check_key: ClassVar[str] = "voicebox_tts"
    enabled_config_key: ClassVar[str] = "voicebox"

    async def _execute(self, data: str) -> dict:
        """Synthesize data (text) and return audio path dict.

        Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
        command code.

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
        import tempfile
        from pathlib import Path as _Path

        server_url = _get_server_url()
        profile_id = _get_default_profile()
        out_base = _Path(tempfile.mkdtemp(prefix="srp-tts-")) / "audio"

        def _synth() -> _Path:
            """Document the synth rule at the boundary where callers use it.

            Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
            command code.

            Returns:
                Resolved filesystem path, or None when the optional path is intentionally absent.

            Examples:
                Input:
                    _synth()
                Output:
                    Path("report.html")
            """
            return write_audio(
                data,
                out_base=out_base,
                api_base=server_url,
                profile_id=profile_id,
            )

        audio_path = await asyncio.to_thread(_synth)
        return {"audio_path": audio_path, "profile": profile_id}
