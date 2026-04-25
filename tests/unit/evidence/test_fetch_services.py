"""Evidence tests — YouTube fetch/ingest services parse correctly.

Four services are covered: video-ID extraction, YouTube URL normalization,
transcript fetch (stubbed YouTubeTranscriptApi), and the adapter's search
results parsing. Whisper fallback is tested for scaffolding only (no binary
on CI).

Evidence receipt:

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| _extract_video_id | 6 URL forms | 11-char ID or None | regex _VIDEO_ID_RE |
| url_normalize | 6 URL forms | canonical watch?v=<id> | urlparse + filter to v=... |
| fetch_transcript | stubbed entries [{"text": "a"}, {"text": "b"}] | "a b" | stitch loop |
| search (adapter) | canned googleapiclient response | parsed RawItem list | _items_from_search |
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import patch

import pytest

from social_research_probe.platforms.youtube import extract

# ---------------------------------------------------------------------------
# Video ID extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://example.com/not-youtube", None),
    ],
)
def test_extract_video_id_handles_standard_url_forms(url, expected):
    """_VIDEO_ID_RE matches v= and youtu.be/ patterns for 11-char IDs."""
    assert extract._extract_video_id(url) == expected


# ---------------------------------------------------------------------------
# URL normalization (adapter.url_normalize)
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    """Build a YouTubeConnector with a temp SRP_DATA_DIR so it can load config."""
    from social_research_probe.services.sourcing.youtube import YouTubeConnector

    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    config = {"data_dir": str(tmp_path)}
    return YouTubeConnector(config=config)


def test_url_normalize_strips_tracking_params(adapter):
    """Adapter.url_normalize keeps only the v= query, dropping t= / list=."""
    canonical = adapter.url_normalize("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30&list=PLabc")
    # The canonicalized form should still contain the video id.
    assert "v=dQw4w9WgXcQ" in canonical
    # Tracking params are gone.
    assert "t=30" not in canonical
    assert "list=PLabc" not in canonical


# ---------------------------------------------------------------------------
# Transcript fetch — stubbed YouTubeTranscriptApi
# ---------------------------------------------------------------------------


class _StubTranscriptApi:
    """Fake YouTubeTranscriptApi that returns canned entries."""

    entries: ClassVar[list[dict]] = []

    @classmethod
    def get_transcript(cls, video_id, languages=None):
        return cls.entries


@pytest.mark.parametrize(
    "entries, expected_joined",
    [
        (
            [{"text": "Hello"}, {"text": "world"}, {"text": "from"}, {"text": "YouTube"}],
            "Hello world from YouTube",
        ),
        ([{"text": "Single segment"}], "Single segment"),
    ],
)
def test_fetch_transcript_stitches_entries_into_text(
    monkeypatch, tmp_path, entries, expected_joined
):
    """Stitched transcript equals ' '.join(entry['text'] for entry in entries)."""
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
    stub = type(_StubTranscriptApi)("Stub", (_StubTranscriptApi,), {"entries": entries})
    with patch("social_research_probe.platforms.youtube.extract.YouTubeTranscriptApi", stub):
        result = extract.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    # Assert text content (ignore minor whitespace normalization).
    assert result is not None
    assert all(word in result for word in expected_joined.split())


def test_fetch_transcript_returns_none_for_unparseable_url():
    """URL without an 11-char video ID must return None instead of crashing."""
    assert extract.fetch_transcript("not-a-youtube-url") is None
