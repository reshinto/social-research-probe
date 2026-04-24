"""yt-dlp audio download technology adapter."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.display.progress import log

_bot_hint_shown = False


def _log_ytdlp_failure(stderr: str) -> None:
    """Log a diagnostic when yt-dlp audio download fails."""
    global _bot_hint_shown
    if not stderr:
        return
    if "Sign in to confirm" in stderr:
        if not _bot_hint_shown:
            _bot_hint_shown = True
            log(
                "[srp] whisper: yt-dlp hit YouTube bot-check — audio transcription unavailable.\n"
                "  Fix: export SRP_YTDLP_COOKIES_FILE=/path/to/cookies.txt"
                " or SRP_YTDLP_BROWSER=chrome"
            )
    else:
        first_line = stderr.strip().splitlines()[0] if stderr.strip() else ""
        if first_line:
            log(f"[srp] whisper: yt-dlp failed: {first_line}")


def download_audio(url: str, tmpdir: str) -> Path | None:
    """Download audio from url into tmpdir; return path to mp3 file or None."""
    audio_path = os.path.join(tmpdir, "audio.%(ext)s")
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--output", audio_path,
        "--no-playlist",
        "--quiet",
        "--no-warnings",
    ]
    cookies_file = os.environ.get("SRP_YTDLP_COOKIES_FILE")
    if cookies_file:
        cmd += ["--cookies", cookies_file]
    else:
        browser = os.environ.get("SRP_YTDLP_BROWSER", "none")
        if browser and browser.lower() != "none":
            cmd += ["--cookies-from-browser", browser]
    cmd.append(url)
    dl = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if dl.returncode != 0:
        _log_ytdlp_failure(dl.stderr)
        return None
    mp3_files = [f for f in os.listdir(tmpdir) if f.endswith(".mp3")]
    if not mp3_files:
        return None
    return Path(tmpdir) / mp3_files[0]


class YtDlpFetch(BaseTechnology[str, Path]):
    """Download audio from a video URL via yt-dlp; return local audio file path.

    Input: video URL string.
    Output: Path to the downloaded mp3 file (inside a temp dir managed by caller),
            or None on failure.
    """

    name: ClassVar[str] = "yt_dlp"
    health_check_key: ClassVar[str] = "yt_dlp"
    enabled_config_key: ClassVar[str] = "yt_dlp"

    async def _execute(self, data: str) -> Path:
        """Download audio from data (video URL) to a temp dir."""
        import asyncio
        with tempfile.TemporaryDirectory(prefix="srp-ytdlp-") as tmpdir:
            result = await asyncio.to_thread(download_audio, data, tmpdir)
            if result is None:
                raise RuntimeError(f"yt-dlp failed to download: {data}")
            # Copy to a stable location since TemporaryDirectory cleans up on exit
            stable = Path(tempfile.mkdtemp(prefix="srp-audio-")) / result.name
            stable.write_bytes(result.read_bytes())
            return stable
