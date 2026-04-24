"""macOS say command TTS technology adapter."""

from __future__ import annotations

import contextlib
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.technologies.base import BaseTechnology


def list_voices() -> list[str]:
    """Return available macOS TTS voice names."""
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
    """Synthesize text via macOS say command and write to out_path (aiff)."""
    subprocess.run(
        ["say", "-v", voice, "-o", str(out_path), text],
        check=True,
        timeout=120,
    )


class MacTTS(BaseTechnology[str, Path]):
    """Synthesize text to audio via the macOS say command.

    Input: text string.
    Output: Path to synthesized audio file.
    Voice configurable via config.tts.mac.voice (default: Alex).
    """

    name: ClassVar[str] = "mac_tts"
    health_check_key: ClassVar[str] = "mac_tts"
    enabled_config_key: ClassVar[str] = "mac_tts"

    async def _execute(self, data: str) -> Path:
        """Synthesize data (text) using macOS say command."""
        import asyncio

        cfg = load_active_config()
        voice = "Alex"
        with contextlib.suppress(AttributeError, TypeError):
            voice = cfg.tunables.get("tts", {}).get("mac", {}).get("voice", "Alex")  # type: ignore[attr-defined]
        out_path = Path(tempfile.mkdtemp(prefix="srp-mactts-")) / "audio.aiff"

        await asyncio.to_thread(synthesize_mac, data, voice, out_path)
        return out_path
