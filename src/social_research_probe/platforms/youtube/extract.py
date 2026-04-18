"""yt-dlp-based transcript extraction. Lazy — only invoked by claim extraction (P6)."""
from __future__ import annotations


def fetch_transcript(url: str) -> str | None:  # pragma: no cover — network
    try:
        import yt_dlp
    except ImportError:
        return None
    opts = {"quiet": True, "skip_download": True, "writesubtitles": True, "subtitleslangs": ["en"]}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    subs = info.get("subtitles") or info.get("automatic_captions") or {}
    if "en" not in subs:
        return None
    return "\n".join(sub.get("data", "") for sub in subs["en"] if isinstance(sub, dict))
