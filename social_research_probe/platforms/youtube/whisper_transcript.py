"""Whisper-based transcript fallback for YouTube videos.

Used when YouTube provides no captions. Downloads the audio track via
yt-dlp and transcribes it locally using OpenAI Whisper + ffmpeg.

Both ``openai-whisper`` and ``ffmpeg`` must be installed for this to work.
All failures return ``None`` so callers can degrade gracefully.
"""

from __future__ import annotations

import os
import subprocess
import tempfile

from social_research_probe.platforms.youtube.extract import _extract_video_id
from social_research_probe.utils.pipeline_cache import (
    get_str,
    set_str,
    whisper_cache,
)
from social_research_probe.utils.progress import log

_bot_hint_shown = False

# Whisper model loading takes ~10-15s per call; reuse the instance across
# fallback invocations within a single process. Keyed by (module_id, name) so
# each test's monkeypatched whisper module gets its own cache slot and
# production imports hit the same singleton every time.
_MODEL_CACHE: dict[tuple[int, str], object] = {}


def _load_model_cached(whisper_module, name: str):
    key = (id(whisper_module), name)
    cached = _MODEL_CACHE.get(key)
    if cached is None:
        cached = whisper_module.load_model(name)
        _MODEL_CACHE[key] = cached
    return cached


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


def fetch_transcript_whisper(url: str) -> str | None:
    """Download audio from *url* and return a Whisper transcript, or None on failure.

    Steps:
    1. Check the on-disk Whisper cache for a prior transcript of this video.
    2. Download audio-only stream via yt-dlp (mp3 format).
    3. Load the Whisper ``base`` model and transcribe the file.
    4. Persist the transcript to cache and return it.

    Returns None if openai-whisper is not installed, yt-dlp download fails,
    or the transcription produces no text.
    """
    try:
        import whisper
    except ImportError:
        return None

    video_id = _extract_video_id(url)
    cache = whisper_cache() if video_id else None
    if cache is not None:
        cached = get_str(cache, video_id)
        if cached is not None:
            log(f"[srp] whisper: cache hit for {video_id}")
            return cached

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.%(ext)s")
        log(f"[srp] yt-dlp: downloading audio for whisper transcription: {url}")
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "--output",
            audio_path,
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
        dl = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if dl.returncode != 0:
            _log_ytdlp_failure(dl.stderr)
            return None

        mp3_files = [f for f in os.listdir(tmpdir) if f.endswith(".mp3")]
        if not mp3_files:
            return None

        audio_file = os.path.join(tmpdir, mp3_files[0])
        log("[srp] whisper: loading model and transcribing audio (this may take a minute)")
        model = _load_model_cached(whisper, "base")
        result = model.transcribe(audio_file, language="en", fp16=False)
        text = (result.get("text") or "").strip()
        if text and cache is not None and video_id:
            set_str(cache, video_id, text)
        return text if text else None
