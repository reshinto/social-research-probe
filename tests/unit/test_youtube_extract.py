"""Tests for social_research_probe.platforms.youtube.extract.

Covers:
- ``fetch_transcript`` via youtube-transcript-api (monkeypatched)
- ``_extract_video_id`` URL parsing
- ``get_transcript`` wrapper delegation
- Graceful None return on API errors and malformed URLs
- _fake_test_transcript integration-test helper
"""

from __future__ import annotations

import social_research_probe.platforms.youtube.extract as yt_extract


class _MockAPI:
    """Stand-in for YouTubeTranscriptApi that returns canned entries."""

    def __init__(self, entries):
        self._entries = entries

    def get_transcript(self, video_id, languages=None):
        return self._entries


class _ErrorAPI:
    """Stand-in that raises the given exception on get_transcript."""

    def __init__(self, exc):
        self._exc = exc

    def get_transcript(self, video_id, languages=None):
        raise self._exc


# ── _extract_video_id ────────────────────────────────────────────────────────


def test_extract_video_id_watch_url():
    assert (
        yt_extract._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    )


def test_extract_video_id_short_url():
    assert yt_extract._extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_returns_none_for_non_youtube():
    assert yt_extract._extract_video_id("https://vimeo.com/12345") is None


def test_extract_video_id_returns_none_for_empty():
    assert yt_extract._extract_video_id("") is None


# ── fetch_transcript ─────────────────────────────────────────────────────────


def test_fetch_transcript_joins_entries(monkeypatch):
    """Joins text entries from the API with newlines."""
    monkeypatch.setattr(
        yt_extract,
        "YouTubeTranscriptApi",
        _MockAPI([{"text": "Hello"}, {"text": "world"}]),
    )
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", True)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result == "Hello\nworld"


def test_fetch_transcript_uses_cache_on_second_call(monkeypatch, tmp_path):
    """Second call for the same video_id hits the on-disk cache — no API call."""
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)

    api_calls = [0]

    class _CountingAPI:
        def get_transcript(self, video_id, languages=None):
            api_calls[0] += 1
            return [{"text": "Hello"}, {"text": "world"}]

    monkeypatch.setattr(yt_extract, "YouTubeTranscriptApi", _CountingAPI())
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", True)

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    first = yt_extract.fetch_transcript(url)
    second = yt_extract.fetch_transcript(url)

    assert first == second == "Hello\nworld"
    assert api_calls[0] == 1


def test_fetch_transcript_skips_blank_entries(monkeypatch):
    """Entries with empty text are excluded from the joined result."""
    monkeypatch.setattr(
        yt_extract,
        "YouTubeTranscriptApi",
        _MockAPI([{"text": "Hello"}, {"text": "  "}, {"text": "world"}]),
    )
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", True)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result == "Hello\nworld"


def test_fetch_transcript_returns_none_when_api_unavailable(monkeypatch):
    """Returns None without calling the API when the package is not installed."""
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", False)
    assert yt_extract.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is None


def test_fetch_transcript_returns_none_on_malformed_url(monkeypatch):
    """Returns None and logs when video ID cannot be parsed from the URL."""
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", True)
    logged: list[str] = []
    monkeypatch.setattr(yt_extract, "log", logged.append)
    result = yt_extract.fetch_transcript("https://notayoutube.com/video/123")
    assert result is None
    assert any("cannot parse video id" in m for m in logged)


def test_fetch_transcript_returns_none_on_api_exception(monkeypatch):
    """Returns None and logs the exception class name on any API error."""
    monkeypatch.setattr(yt_extract, "YouTubeTranscriptApi", _ErrorAPI(ValueError("no transcript")))
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", True)
    logged: list[str] = []
    monkeypatch.setattr(yt_extract, "log", logged.append)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result is None
    assert any("ValueError" in m for m in logged)


def test_fetch_transcript_logs_transcripts_disabled(monkeypatch):
    """Logs the exception class name when a transcripts-disabled-style error is raised."""

    class TranscriptsDisabledError(Exception):
        pass

    monkeypatch.setattr(
        yt_extract, "YouTubeTranscriptApi", _ErrorAPI(TranscriptsDisabledError("vid"))
    )
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", True)
    logged: list[str] = []
    monkeypatch.setattr(yt_extract, "log", logged.append)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result is None
    assert any("TranscriptsDisabledError" in m for m in logged)


def test_fetch_transcript_returns_none_when_all_entries_empty(monkeypatch):
    """Returns None when all transcript entries have blank text."""
    monkeypatch.setattr(
        yt_extract, "YouTubeTranscriptApi", _MockAPI([{"text": "  "}, {"text": "\n"}])
    )
    monkeypatch.setattr(yt_extract, "_API_AVAILABLE", True)
    assert yt_extract.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is None


# ── get_transcript wrapper ───────────────────────────────────────────────────


def test_get_transcript_builds_correct_url(monkeypatch):
    """get_transcript passes a URL containing the video_id to fetch_transcript."""
    captured: list[str] = []

    def fake_fetch(url: str) -> str | None:
        captured.append(url)
        return "some transcript"

    monkeypatch.setattr(yt_extract, "fetch_transcript", fake_fetch)
    video_id = "dQw4w9WgXcQ"
    yt_extract.get_transcript(video_id)
    assert len(captured) == 1
    assert video_id in captured[0]


def test_get_transcript_propagates_none(monkeypatch):
    """get_transcript returns None when fetch_transcript returns None."""
    monkeypatch.setattr(yt_extract, "fetch_transcript", lambda url: None)
    assert yt_extract.get_transcript("any_video_id") is None


def test_get_transcript_propagates_text(monkeypatch):
    """get_transcript returns the transcript text unchanged."""
    monkeypatch.setattr(yt_extract, "fetch_transcript", lambda url: "transcript text")
    assert yt_extract.get_transcript("some_id") == "transcript text"


# ── _fake_test_transcript ────────────────────────────────────────────────────


def test_fake_transcript_disabled_by_default():
    """_fake_test_transcript returns None unless SRP_TEST_USE_FAKE_YOUTUBE is set."""
    assert yt_extract._fake_test_transcript("https://www.youtube.com/watch?v=fake") is None


def test_fake_transcript_returns_deterministic_text(monkeypatch):
    """Returns a deterministic transcript when the env var is set and URL matches."""
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    result = yt_extract._fake_test_transcript("https://www.youtube.com/watch?v=fake-video")
    assert result is not None
    assert "transcript-token-1" in result


def test_fake_transcript_returns_none_for_non_fake_url(monkeypatch):
    """Returns None for a real URL even when SRP_TEST_USE_FAKE_YOUTUBE is set."""
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    assert yt_extract._fake_test_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is None
