"""YouTube transcript extraction via yt-dlp.

Fetches the English transcript for a YouTube video so the rest of the
pipeline can use real spoken content (instead of just the YouTube
description snippet) for one-line summaries and claim extraction.

The implementation is intentionally tolerant: any failure (yt-dlp not
installed, no English track, network error, malformed subtitle file)
returns ``None`` so callers can fall back gracefully.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.request

from social_research_probe.utils.progress import log


def fetch_transcript(url: str) -> str | None:
    """Return the cleaned English transcript text for *url*, or None on failure.

    YouTube increasingly bot-blocks unauthenticated requests with
    "Sign in to confirm you're not a bot". We work around this by telling
    yt-dlp to read cookies from a browser configured via the
    ``SRP_YTDLP_BROWSER`` env var (e.g. ``safari``, ``chrome``).
    Defaults to no cookies to avoid macOS sandbox permission errors.
    """
    if fake := _fake_test_transcript(url):
        return fake
    try:
        import yt_dlp
    except ImportError:
        return None

    log(f"[srp] yt-dlp: fetching captions for {url}")
    opts = _yt_dlp_opts()
    for attempt_opts in [opts, {**opts, "cookiesfrombrowser": None}]:
        try:
            with yt_dlp.YoutubeDL(attempt_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception:
            continue
        subs = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}
        en_tracks = subs.get("en") or auto.get("en") or []
        if en_tracks:
            text = _extract_text(en_tracks)
            if text:
                return text
    return None


def _yt_dlp_opts() -> dict:
    """Build yt-dlp options. Includes browser-cookie auth when available."""
    opts: dict = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
        "no_warnings": True,
    }
    browser = os.environ.get("SRP_YTDLP_BROWSER", "none")
    if browser and browser.lower() != "none":
        opts["cookiesfrombrowser"] = (browser,)
    return opts


def _fake_test_transcript(url: str) -> str | None:
    """Return a deterministic transcript for subprocess integration tests."""
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") != "1":
        return None
    if "watch?v=fake" not in url:
        return None
    tokens = " ".join(f"transcript-token-{i}" for i in range(1, 260))
    return f"Deterministic transcript for integration testing. {tokens}"


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
    """Download the subtitle file at *url* and return cleaned plain text.

    YouTube serves several subtitle formats: VTT/SRT for manual captions,
    and json3/srv3 for auto-generated ones. Parse each to plain text so
    downstream consumers see a flat string regardless of source format.
    """
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return None
    if ext in {"vtt", "srt"}:
        return _strip_vtt(raw)
    if ext in {"json3", "srv3", "srv2", "srv1"}:
        return _parse_json3(raw)
    return raw


def _parse_json3(raw: str) -> str | None:
    """Parse a YouTube json3/srv3 caption file into plain text."""
    import json

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    events = payload.get("events") or []
    lines: list[str] = []
    for event in events:
        segs = event.get("segs") or []
        text = "".join(seg.get("utf8", "") for seg in segs if isinstance(seg, dict))
        cleaned = text.strip()
        if cleaned and (not lines or lines[-1] != cleaned):
            lines.append(cleaned)
    return " ".join(lines) or None


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
