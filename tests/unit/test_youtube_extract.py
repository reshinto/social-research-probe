"""Tests for social_research_probe.platforms.youtube.extract.

What is verified here:
    - ``get_transcript`` builds the correct YouTube watch URL from a video ID
      and passes it to ``fetch_transcript``.
    - ``None`` returned by ``fetch_transcript`` propagates unchanged through
      ``get_transcript`` (e.g. when yt-dlp is absent or no English track exists).
    - A transcript string returned by ``fetch_transcript`` is surfaced
      unchanged by ``get_transcript``.

The live network call in ``fetch_transcript`` is intentionally excluded from
these tests (it carries ``# pragma: no cover — network``). All tests use
monkeypatching so no network access is required.
"""
from __future__ import annotations

import social_research_probe.platforms.youtube.extract as yt_extract


def test_get_transcript_builds_url(monkeypatch: object) -> None:
    """get_transcript passes a URL containing the video_id to fetch_transcript.

    Args:
        monkeypatch: pytest fixture for temporarily replacing attributes.
    """
    captured: list[str] = []

    def fake_fetch(url: str) -> str | None:
        captured.append(url)
        return "some transcript"

    monkeypatch.setattr(yt_extract, "fetch_transcript", fake_fetch)

    video_id = "dQw4w9WgXcQ"
    yt_extract.get_transcript(video_id)

    assert len(captured) == 1
    assert video_id in captured[0]


def test_get_transcript_returns_none_on_import_error(monkeypatch: object) -> None:
    """get_transcript returns None when fetch_transcript returns None.

    Args:
        monkeypatch: pytest fixture for temporarily replacing attributes.
    """
    monkeypatch.setattr(yt_extract, "fetch_transcript", lambda url: None)

    result = yt_extract.get_transcript("any_video_id")

    assert result is None


def test_get_transcript_returns_text(monkeypatch: object) -> None:
    """get_transcript returns the transcript text from fetch_transcript unchanged.

    Args:
        monkeypatch: pytest fixture for temporarily replacing attributes.
    """
    expected = "transcript text"
    monkeypatch.setattr(yt_extract, "fetch_transcript", lambda url: expected)

    result = yt_extract.get_transcript("some_id")

    assert result == expected
