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
from typing import ClassVar

from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.pipeline_cache import (
    get_str,
    set_str,
    transcript_cache,
)
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

    Transcripts are cached by video_id on disk so repeat research runs on the
    same topic skip the network call entirely. Cache lookup is skipped for
    fake-test URLs so integration tests remain deterministic.
    """
    if fake := _fake_test_transcript(url):
        return fake
    if not _API_AVAILABLE:
        return None
    video_id = _extract_video_id(url)
    if not video_id:
        log(f"[srp] captions: cannot parse video id from {url}")
        return None
    cache = transcript_cache()
    cached = get_str(cache, video_id)
    if cached is not None:
        log(f"[srp] captions: cache hit for {video_id}")
        return cached
    log(f"[srp] captions: fetching via youtube-transcript-api for {url}")
    try:
        entries = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
        text = "\n".join(e["text"] for e in entries if e.get("text", "").strip())
        if text:
            set_str(cache, video_id, text)
            return text
        return None
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


class YoutubeTranscriptFetch(BaseTechnology[str, str]):
    """Fetch YouTube video transcript via youtube-transcript-api.

    Input: video URL or video ID string.
    Output: transcript text string, or None on failure.
    """

    name: ClassVar[str] = "youtube_transcript_api"
    health_check_key: ClassVar[str] = "youtube_transcript_api"
    enabled_config_key: ClassVar[str] = "youtube_transcript_api"

    async def _execute(self, data: str) -> str:
        """Fetch transcript for the given YouTube URL or video ID."""
        import asyncio
        result = await asyncio.to_thread(fetch_transcript, data)
        if result is None:
            raise RuntimeError(f"No transcript available for: {data}")
        return result
