"""Evidence test — corroboration source-quality filters.

Covers two classes of invalid evidence the pipeline used to accept silently:

1. **Self-source.** A claim extracted from a YouTube video cannot be
   corroborated by the same video (or anything else on the same host).
2. **Video-hosting domains.** Search backends only see ``{url, title, snippet}``
   and cannot read video content. URLs on youtube.com / vimeo.com / tiktok.com
   etc. are keyword matches against author-authored marketing text, not
   verifiable evidence. They must be excluded entirely.

Evidence receipt (what / expected / why):

| Case | Input | Expected | Why |
| --- | --- | --- | --- |
| Brave self-source | claim source_url = ``https://www.youtube.com/watch?v=ABC123``; response contains [source_url, another youtube.com URL, an arxiv URL] | sources == ``["https://arxiv.org/abs/2401.12345"]`` | self-source drops the exact URL; video-domain drops the other youtube result; arxiv is a text source and is retained |
| Tavily video-domain | claim source_url = ``https://example.com/post``; response contains [youtube, vimeo, tiktok, nature.com] | sources == ``["https://www.nature.com/articles/s41586-024-00000-0"]`` | three video hosts excluded; nature.com is the one text source |
| Exa no-source defensive | claim source_url = None; response contains [youtube, arxiv] | sources == ``["https://arxiv.org/abs/2401.99999"]`` | video-domain filter applies independent of self-source |
"""

from __future__ import annotations

import httpx
import pytest
import respx

from social_research_probe.corroboration._filters import (
    filter_results,
    is_self_source,
    is_video_url,
)
from social_research_probe.corroboration.brave import BraveBackend
from social_research_probe.corroboration.exa import ExaBackend
from social_research_probe.corroboration.tavily import TavilyBackend
from social_research_probe.validation.claims import Claim


def _claim(text: str, source_url: str | None) -> Claim:
    return Claim(text=text, source_text=text, index=0, source_url=source_url)


@pytest.mark.anyio
async def test_brave_excludes_self_source_and_video_domain(monkeypatch):
    """Brave drops self-source + sibling-video results; arxiv is kept."""
    monkeypatch.setenv("SRP_BRAVE_API_KEY", "test-key")
    source_url = "https://www.youtube.com/watch?v=ABC123"
    payload = {
        "web": {
            "results": [
                {"url": source_url},
                {"url": "https://www.youtube.com/watch?v=XYZ789"},
                {"url": "https://arxiv.org/abs/2401.12345"},
            ]
        }
    }
    with respx.mock:
        respx.get("https://api.search.brave.com/res/v1/web/search").mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await BraveBackend().corroborate(_claim("test claim", source_url))
    assert result.sources == ["https://arxiv.org/abs/2401.12345"]
    assert result.verdict == "supported"


@pytest.mark.anyio
async def test_tavily_excludes_video_hosts_when_source_is_text(monkeypatch):
    """Tavily drops youtube/vimeo/tiktok even when the source is a text page."""
    monkeypatch.setenv("SRP_TAVILY_API_KEY", "test-key")
    payload = {
        "results": [
            {"url": "https://www.youtube.com/watch?v=AAA"},
            {"url": "https://vimeo.com/111111"},
            {"url": "https://www.tiktok.com/@user/video/222"},
            {"url": "https://www.nature.com/articles/s41586-024-00000-0"},
        ]
    }
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await TavilyBackend().corroborate(
            _claim("test claim", "https://example.com/post")
        )
    assert result.sources == ["https://www.nature.com/articles/s41586-024-00000-0"]
    assert result.verdict == "supported"


@pytest.mark.anyio
async def test_exa_filters_video_domain_when_source_url_is_none(monkeypatch):
    """Video-domain filter runs independent of self-source; no source_url ⇒ still strip youtube."""
    monkeypatch.setenv("SRP_EXA_API_KEY", "test-key")
    payload = {
        "results": [
            {"url": "https://www.youtube.com/watch?v=BBB"},
            {"url": "https://arxiv.org/abs/2401.99999"},
        ]
    }
    with respx.mock:
        respx.post("https://api.exa.ai/search").mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await ExaBackend().corroborate(_claim("test claim", None))
    assert result.sources == ["https://arxiv.org/abs/2401.99999"]
    assert result.verdict == "supported"


# Defensive-branch micro-tests on the filter helpers themselves.
# Each input maps to an exact output — the "why" is that the helpers are defined
# to return False/None on malformed or absent input so callers never crash.


def test_is_video_url_returns_false_for_empty_and_malformed_urls():
    assert is_video_url("") is False
    assert is_video_url("http://[::1") is False  # urlparse raises ValueError
    assert is_video_url("not-a-url") is False


def test_is_self_source_returns_false_when_either_host_is_unresolvable():
    assert is_self_source("not-a-url", "https://example.com") is False
    assert is_self_source("https://example.com", "also-not-a-url") is False


def test_filter_results_keeps_items_without_a_url_as_passthrough_metadata():
    raw = [
        {"url": ""},  # explicit empty URL → kept
        {"title": "orphan without url"},  # no url key → kept
        {"url": "https://example.com/article"},  # normal → kept
    ]
    kept, self_excluded, video_excluded = filter_results(raw, None)
    assert len(kept) == 3
    assert self_excluded == 0
    assert video_excluded == 0
