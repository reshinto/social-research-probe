"""macOS say command TTS technology adapter."""

from __future__ import annotations

import contextlib
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.technologies import BaseTechnology


def list_voices() -> list[str]:
    """Return available macOS TTS voice names.

    Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
    command code.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            list_voices()
        Output:
            ["AI safety", "model evaluation"]
    """
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=10)
        voices = []
        for line in result.stdout.splitlines():
            if line.strip():
                voices.append(line.split()[0])
        return voices
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def synthesize_mac(text: str, voice: str, out_path: Path) -> None:
    """Synthesize text via macOS say command and write to out_path (aiff).

    Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
    command code.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        voice: System voice name requested for local speech synthesis.
        out_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            synthesize_mac(
                text="This tool reduces latency by 30%.",
                voice="AI safety",
                out_path=Path("report.html"),
            )
        Output:
            None
    """
    subprocess.run(
        ["say", "-v", voice, "-o", str(out_path), text],
        check=True,
        timeout=120,
    )


class MacTTS(BaseTechnology[str, Path]):
    """Synthesize text to audio via the macOS say command.

    Input: text string. Output: Path to synthesized audio file. Voice configurable
    via config.tts.mac.voice (default: Alex).

    Examples:
        Input:
            MacTTS
        Output:
            MacTTS
    """

    name: ClassVar[str] = "mac_tts"
    health_check_key: ClassVar[str] = "mac_tts"
    enabled_config_key: ClassVar[str] = "mac_tts"

    async def _execute(self, data: str) -> Path:
        """Synthesize data (text) using macOS say command.

        Text-to-speech helpers isolate Voicebox and platform audio details from report rendering and
        command code.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Resolved filesystem path, or None when the optional path is intentionally absent.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                Path("report.html")
        """
        import asyncio

        cfg = load_active_config()
        voice = "Alex"
        with contextlib.suppress(AttributeError, TypeError):
            voice = cfg.tunables.get("tts", {}).get("mac", {}).get("voice", "Alex")  # type: ignore[attr-defined]
        out_path = Path(tempfile.mkdtemp(prefix="srp-mactts-")) / "audio.aiff"

        await asyncio.to_thread(synthesize_mac, data, voice, out_path)
        return out_path
