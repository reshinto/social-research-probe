"""YouTube transcript extraction via youtube-transcript-api.

Fetches the English transcript for a YouTube video so the rest of the
pipeline can use real spoken content for one-line summaries and claim
extraction. Uses youtube-transcript-api, which accesses YouTube's public
timedtext endpoint without requiring yt-dlp or browser cookies.

Any failure returns None so callers can fall back gracefully.
"""

from __future__ import annotations

import os
import re

from social_research_probe.utils.progress import log

_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")

try:
    from youtube_transcript_api import YouTubeTranscriptApi

    _API_AVAILABLE = True
except ImportError:
    YouTubeTranscriptApi = None
    _API_AVAILABLE = False


def _extract_video_id(url: str) -> str | None:
    """Return the 11-character YouTube video ID from a URL, or None."""
    m = _VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def fetch_transcript(url: str) -> str | None:
    """Return the cleaned English transcript text for *url*, or None on failure.

    Uses youtube-transcript-api to access YouTube's public timedtext
    endpoint. Does not require cookies or yt-dlp for the caption path.
    """
    if fake := _fake_test_transcript(url):
        return fake
    if not _API_AVAILABLE:
        return None
    video_id = _extract_video_id(url)
    if not video_id:
        log(f"[srp] captions: cannot parse video id from {url}")
        return None
    log(f"[srp] captions: fetching via youtube-transcript-api for {url}")
    try:
        entries = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
        text = "\n".join(e["text"] for e in entries if e.get("text", "").strip())
        return text or None
    except Exception as exc:
        log(f"[srp] captions: unavailable for {url} ({type(exc).__name__})")
        return None


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
