"""YouTube transcript extraction via youtube-transcript-api.

Fetches the English transcript for a YouTube video so the rest of the
pipeline can use real spoken content for one-line summaries and claim
extraction. Uses youtube-transcript-api, which accesses YouTube's public
timedtext endpoint without requiring yt-dlp or browser cookies.

Any failure returns None so callers can fall back gracefully.
"""

from __future__ import annotations

import os
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.core.youtube import youtube_video_id_from_url
from social_research_probe.utils.display.progress import log

try:
    from youtube_transcript_api import YouTubeTranscriptApi

    _API_AVAILABLE = True
except ImportError:
    YouTubeTranscriptApi = None
    _API_AVAILABLE = False


def fetch_transcript(url: str) -> str | None:
    """Return the cleaned English transcript text for *url*, or None on failure.

    Uses youtube-transcript-api to access YouTube's public timedtext endpoint. Does not
    require cookies or yt-dlp for the caption path.

    Cache lookup is skipped for fake-test URLs so integration tests remain deterministic.

    Args:
        url: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            fetch_transcript(
                url="https://youtu.be/abc123",
            )
        Output:
            "AI safety"
    """
    if fake := _fake_test_transcript(url):
        return fake
    if not _API_AVAILABLE:
        return None
    video_id = youtube_video_id_from_url(url)
    if not video_id:
        log(f"[srp] captions: cannot parse video id from {url}")
        return None
    log(f"[srp] captions: fetching via youtube-transcript-api for {url}")
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB"])
        text = "\n".join(snippet.text for snippet in fetched if snippet.text.strip())
        if text:
            return text
        return None
    except Exception as exc:
        log(f"[srp] captions: unavailable for {url} ({type(exc).__name__})")
        return None


def _fake_test_transcript(url: str) -> str | None:
    """Return a deterministic transcript for subprocess integration tests.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        url: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _fake_test_transcript(
                url="https://youtu.be/abc123",
            )
        Output:
            "AI safety"
    """
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") != "1":
        return None
    if "watch?v=fake" not in url:
        return None
    tokens = " ".join(f"transcript-token-{i}" for i in range(1, 260))
    return f"Deterministic transcript for integration testing. {tokens}"


def get_transcript(video_id: str) -> str | None:
    """Return the English transcript for a YouTube video ID.

    Fetch adapters hide provider response details and give services the stable source-item shape the
    rest of the project expects.

    Args:
        video_id: YouTube video id whose metadata, transcript, comments, or claims are being
                  fetched.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            get_transcript(
                video_id="abc123",
            )
        Output:
            "AI safety"
    """
    return fetch_transcript(f"https://www.youtube.com/watch?v={video_id}")


class YoutubeTranscriptFetch(BaseTechnology[str, str]):
    """Fetch YouTube video transcript via youtube-transcript-api.

    Input: video URL or video ID string. Output: transcript text string, or None on failure.

    Examples:
        Input:
            YoutubeTranscriptFetch
        Output:
            YoutubeTranscriptFetch
    """

    name: ClassVar[str] = "youtube_transcript_api"
    health_check_key: ClassVar[str] = "youtube_transcript_api"
    enabled_config_key: ClassVar[str] = "youtube_transcript_api"

    async def _execute(self, data: str) -> str:
        """Fetch transcript for the given YouTube URL or video ID.

        Fetch adapters hide provider response details and give services the stable source-item shape the
        rest of the project expects.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        import asyncio

        result = await asyncio.to_thread(fetch_transcript, data)
        if result is None:
            raise RuntimeError(f"No transcript available for: {data}")
        return result
