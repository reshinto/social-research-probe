"""Whisper-based transcript fallback for YouTube videos.

Used when YouTube provides no captions. Downloads the audio track via
yt-dlp and transcribes it locally using OpenAI Whisper + ffmpeg.

Both ``openai-whisper`` and ``ffmpeg`` must be installed for this to work.
All failures return ``None`` so callers can degrade gracefully.
"""

from __future__ import annotations

from social_research_probe.utils.progress import log

import os
import subprocess
import tempfile


def fetch_transcript_whisper(url: str) -> str | None:
    """Download audio from *url* and return a Whisper transcript, or None on failure.

    Steps:
    1. Download audio-only stream via yt-dlp (mp3 format).
    2. Load the Whisper ``base`` model and transcribe the file.
    3. Return the stripped transcript text.

    Returns None if openai-whisper is not installed, yt-dlp download fails,
    or the transcription produces no text.
    """
    try:
        import whisper  # type: ignore[import-untyped]
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.%(ext)s")
        log(f"[srp] yt-dlp: downloading audio for whisper transcription: {url}")
        dl = subprocess.run(
            [
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
                url,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if dl.returncode != 0:
            return None

        mp3_files = [f for f in os.listdir(tmpdir) if f.endswith(".mp3")]
        if not mp3_files:
            return None

        audio_file = os.path.join(tmpdir, mp3_files[0])
        log("[srp] whisper: loading model and transcribing audio (this may take a minute)")
        model = whisper.load_model("base")
        result = model.transcribe(audio_file, language="en", fp16=False)
        text = (result.get("text") or "").strip()
        return text if text else None
