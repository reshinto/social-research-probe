"""YouTube transcript extraction via yt-dlp.

Why this file exists:
    Fetching YouTube transcripts requires an optional heavy dependency (yt-dlp)
    and a live network call. This module isolates both concerns so the rest of
    the pipeline can import it without triggering side-effects. It is loaded
    lazily — only when the claim-extraction stage (pipeline step P6) needs to
    pull transcript text for a YouTube source.

Who calls it:
    - ``social_research_probe.platforms.youtube.source`` (YouTube platform adapter)
    - Any pipeline step that needs raw transcript text keyed by video ID.
"""

from __future__ import annotations


def fetch_transcript(url: str) -> str | None:
    """Download and return the English transcript for a YouTube video URL.

    Attempts to retrieve manually-uploaded subtitles first, then falls back to
    auto-generated captions. Returns ``None`` rather than raising when yt-dlp
    is not installed or no English track is available, so callers can degrade
    gracefully.

    Args:
        url: A fully-qualified YouTube watch URL, e.g.
            ``"https://www.youtube.com/watch?v=dQw4w9WgXcQ"``.

    Returns:
        A single string containing all subtitle segments joined by newlines,
        or ``None`` if yt-dlp is unavailable or no English track exists.

    Raises:
        Any exception raised by yt-dlp (network errors, geo-blocking, etc.)
        propagates unmodified to the caller.

    Example::

        text = fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        if text:
            print(text[:200])
    """
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
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Prefer manually uploaded subtitles; fall back to auto-generated captions.
    subs = info.get("subtitles") or info.get("automatic_captions") or {}
    if "en" not in subs:
        return None

    return "\n".join(sub.get("data", "") for sub in subs["en"] if isinstance(sub, dict))


def get_transcript(video_id: str) -> str | None:
    """Return the English transcript for a YouTube video given its video ID.

    Constructs the canonical watch URL from ``video_id`` and delegates to
    :func:`fetch_transcript`. This thin wrapper exists so callers can work with
    bare video IDs (the natural identifier stored in our data model) without
    coupling themselves to URL-construction details.

    Args:
        video_id: The 11-character YouTube video identifier, e.g.
            ``"dQw4w9WgXcQ"``.

    Returns:
        The full English transcript as a string, or ``None`` when the transcript
        cannot be retrieved (missing yt-dlp, no English track, network error).

    Example::

        text = get_transcript("dQw4w9WgXcQ")
        if text:
            print(f"Got {len(text)} chars of transcript")
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    return fetch_transcript(url)
