"""Source-quality filters for corroboration search results.

Two categories of evidence are stripped before any provider computes a verdict:

1. **Self-source.** The claim's own URL (exact match OR same host) must not be
   used to verify itself. Without this filter, a claim extracted from a YouTube
   video can be "supported" by the same video appearing in the Brave/Exa/Tavily
   search results — circular and invalid.

2. **Video-hosting domains.** Search providers return only ``{url, title,
   snippet}`` — they never fetch video content or transcripts. A video URL in
   the result list is at best a keyword match against the author-authored
   title/description, not verifiable evidence. Until a transcript-fetch-verify
   step exists, URLs on known video-hosting domains are excluded entirely.

   Evidence must come from text sources whose snippet reasonably reflects the
   underlying content (articles, papers, standards pages, docs).

Helpers are pure-computation, synchronous, and have no network side-effects.
"""

from __future__ import annotations

from urllib.parse import urlparse

VIDEO_HOST_DOMAINS: frozenset[str] = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "vimeo.com",
        "www.vimeo.com",
        "tiktok.com",
        "www.tiktok.com",
        "m.tiktok.com",
        "rumble.com",
        "www.rumble.com",
        "dailymotion.com",
        "www.dailymotion.com",
        "twitch.tv",
        "www.twitch.tv",
        "m.twitch.tv",
    }
)


def _host(url: str) -> str | None:
    """Return the lowercased hostname of a URL, or None for malformed input."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    return host or None


def is_video_url(url: str) -> bool:
    """True if ``url`` is hosted on a known video platform.

    Video snippets are author-authored marketing text, not verified content,
    so video URLs are not usable as corroboration evidence.
    """
    host = _host(url)
    if host is None:
        return False
    return host in VIDEO_HOST_DOMAINS


def is_self_source(result_url: str, source_url: str | None) -> bool:
    """True if ``result_url`` is the same as ``source_url`` or shares its host."""
    if not source_url:
        return False
    if result_url == source_url:
        return True
    r_host = _host(result_url)
    s_host = _host(source_url)
    if r_host is None or s_host is None:
        return False
    return r_host == s_host


def filter_results(
    raw_results: list[dict],
    source_url: str | None,
    *,
    url_key: str = "url",
) -> tuple[list[dict], int, int]:
    """Drop self-source and video-hosting-domain results from a provider payload.

    Args:
        raw_results: List of provider result dicts; each expected to carry a URL
            under ``url_key``. Items with a missing/empty URL are kept as-is so
            non-URL metadata passes through.
        source_url: The URL the claim was extracted from. May be ``None`` when
            upstream caller did not plumb provenance.
        url_key: Key under which each result carries its URL string.

    Returns:
        ``(filtered, self_excluded, video_excluded)`` — the filtered list plus
        the counts of each exclusion category (useful for DEBUG logging).
    """
    kept: list[dict] = []
    self_excluded = 0
    video_excluded = 0
    for item in raw_results:
        url = str(item.get(url_key) or "")
        if not url:
            kept.append(item)
            continue
        if is_self_source(url, source_url):
            self_excluded += 1
            continue
        if is_video_url(url):
            video_excluded += 1
            continue
        kept.append(item)
    return kept, self_excluded, video_excluded
