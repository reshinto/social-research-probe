"""YouTube transcript extraction via yt-dlp.

Fetches the English transcript for a YouTube video so the rest of the
pipeline can use real spoken content (instead of just the YouTube
description snippet) for one-line summaries and claim extraction.

The implementation is intentionally tolerant: any failure (yt-dlp not
installed, no English track, network error, malformed subtitle file)
returns ``None`` so callers can fall back gracefully.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request


def fetch_transcript(url: str) -> str | None:
    """Return the cleaned English transcript text for *url*, or None on failure."""
    try:
        import yt_dlp
    except ImportError:
        return None

    opts = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return None

    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    en_tracks = subs.get("en") or auto.get("en") or []
    if not en_tracks:
        return None
    return _extract_text(en_tracks)


def get_transcript(video_id: str) -> str | None:
    """Return the English transcript for a YouTube video ID."""
    return fetch_transcript(f"https://www.youtube.com/watch?v={video_id}")


def _extract_text(tracks: list) -> str | None:
    """Return joined transcript text from a list of yt-dlp subtitle entries.

    Each entry is either ``{"data": "..."}`` (used by tests) or
    ``{"url": "...", "ext": "..."}`` (real yt-dlp output). The first
    successfully decoded track wins.
    """
    pieces: list[str] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        if "data" in track:
            pieces.append(track["data"])
            continue
        text = _download_subtitle(track.get("url"), track.get("ext", "vtt"))
        if text:
            pieces.append(text)
            break
    joined = "\n".join(p for p in pieces if p)
    return joined or None


def _download_subtitle(url: str | None, ext: str) -> str | None:
    """Download the subtitle file at *url* and return cleaned plain text."""
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return None
    if ext in {"vtt", "srt"}:
        return _strip_vtt(raw)
    return raw


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_vtt(raw: str) -> str:
    """Strip WEBVTT/SRT timestamps, cue numbers, and inline tags."""
    lines: list[str] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
            continue
        cleaned = _TAG_RE.sub("", line).strip()
        if cleaned and (not lines or lines[-1] != cleaned):
            lines.append(cleaned)
    return " ".join(lines)
