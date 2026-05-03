"""yt-dlp audio download technology adapter."""

from __future__ import annotations

import os
import subprocess
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.display.progress import log


class YtDlpFlag(StrEnum):
    """Yt dlp flag type.

    Examples:
        Input:
            YtDlpFlag
        Output:
            YtDlpFlag
    """

    EXTRACT_AUDIO = "--extract-audio"
    AUDIO_FORMAT = "--audio-format"
    AUDIO_QUALITY = "--audio-quality"
    OUTPUT = "--output"
    NO_PLAYLIST = "--no-playlist"
    QUIET = "--quiet"
    NO_WARNINGS = "--no-warnings"
    COOKIES = "--cookies"
    COOKIES_FROM_BROWSER = "--cookies-from-browser"


_bot_hint_shown = False


def _log_ytdlp_failure(stderr: str) -> None:
    """Log a diagnostic when yt-dlp audio download fails.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        stderr: Captured standard error from the runner process.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _log_ytdlp_failure(
                stderr="AI safety",
            )
        Output:
            None
    """
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
    """Download audio from url into tmpdir; return path to mp3 file or None.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        url: Stable source identifier or URL used to join records across stages and exports.
        tmpdir: Filesystem location used to read, write, or resolve project data.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            download_audio(
                url="https://youtu.be/abc123",
                tmpdir=Path(".skill-data"),
            )
        Output:
            Path("report.html")
    """
    audio_path = os.path.join(tmpdir, "audio.%(ext)s")
    cmd = [
        "yt-dlp",
        YtDlpFlag.EXTRACT_AUDIO,
        YtDlpFlag.AUDIO_FORMAT,
        "mp3",
        YtDlpFlag.AUDIO_QUALITY,
        "0",
        YtDlpFlag.OUTPUT,
        audio_path,
        YtDlpFlag.NO_PLAYLIST,
        YtDlpFlag.QUIET,
        YtDlpFlag.NO_WARNINGS,
    ]
    cookies_file = os.environ.get("SRP_YTDLP_COOKIES_FILE")
    if cookies_file:
        cmd += [YtDlpFlag.COOKIES, cookies_file]
    else:
        browser = os.environ.get("SRP_YTDLP_BROWSER", "none")
        if browser and browser.lower() != "none":
            cmd += [YtDlpFlag.COOKIES_FROM_BROWSER, browser]
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

    Input: video URL string. Output: Path to the downloaded mp3 file (inside a temp dir
    managed by caller), or None on failure.

    Examples:
        Input:
            YtDlpFetch
        Output:
            YtDlpFetch
    """

    name: ClassVar[str] = "yt_dlp"
    health_check_key: ClassVar[str] = "yt_dlp"
    enabled_config_key: ClassVar[str] = "yt_dlp"

    async def _execute(self, data: str) -> Path:
        """Download audio from data (video URL) to a temp dir.

        Fetch adapters hide provider response details and give services the stable source-item shape the
        rest of the project expects.

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

        with tempfile.TemporaryDirectory(prefix="srp-ytdlp-") as tmpdir:
            result = await asyncio.to_thread(download_audio, data, tmpdir)
            if result is None:
                raise RuntimeError(f"yt-dlp failed to download: {data}")
            # Copy to a stable location since TemporaryDirectory cleans up on exit
            stable = Path(tempfile.mkdtemp(prefix="srp-audio-")) / result.name
            stable.write_bytes(result.read_bytes())
            return stable
