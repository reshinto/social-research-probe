"""Tests for social_research_probe.platforms.youtube.extract.

What is verified here:
    - ``get_transcript`` builds the correct YouTube watch URL from a video ID
      and passes it to ``fetch_transcript``.
    - ``None`` returned by ``fetch_transcript`` propagates unchanged through
      ``get_transcript`` (e.g. when yt-dlp is absent or no English track exists).
    - A transcript string returned by ``fetch_transcript`` is surfaced
      unchanged by ``get_transcript``.

The live network call in ``fetch_transcript`` is covered by monkeypatching
yt_dlp.YoutubeDL so no network access is required.
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


class TestExtractTextFromTracks:
    def test_returns_none_when_tracks_empty(self):
        from social_research_probe.platforms.youtube.extract import _extract_text

        assert _extract_text([]) is None

    def test_skips_non_dict_entries(self):
        from social_research_probe.platforms.youtube.extract import _extract_text

        assert _extract_text(["bad", None, 123]) is None

    def test_uses_url_when_no_data_key(self, monkeypatch):
        from social_research_probe.platforms.youtube import extract as ext

        monkeypatch.setattr(ext, "_download_subtitle", lambda url, ext_: "real text")
        result = ext._extract_text([{"url": "https://x", "ext": "vtt"}])
        assert result == "real text"

    def test_returns_none_when_url_download_fails(self, monkeypatch):
        from social_research_probe.platforms.youtube import extract as ext

        monkeypatch.setattr(ext, "_download_subtitle", lambda url, ext_: None)
        assert ext._extract_text([{"url": "https://x", "ext": "vtt"}]) is None


class TestDownloadSubtitle:
    def test_returns_none_when_url_missing(self):
        from social_research_probe.platforms.youtube.extract import _download_subtitle

        assert _download_subtitle(None, "vtt") is None
        assert _download_subtitle("", "vtt") is None

    def test_returns_none_on_url_error(self, monkeypatch):
        import urllib.error
        import urllib.request

        from social_research_probe.platforms.youtube.extract import _download_subtitle

        def boom(*a, **kw):
            raise urllib.error.URLError("net down")

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        assert _download_subtitle("https://x", "vtt") is None

    def test_strips_vtt(self, monkeypatch):
        import urllib.request

        from social_research_probe.platforms.youtube.extract import _download_subtitle

        vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.000\n<c>Hello</c> world\n"

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return vtt.encode("utf-8")

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: _Resp())
        assert _download_subtitle("https://x", "vtt") == "Hello world"

    def test_returns_raw_for_unknown_ext(self, monkeypatch):
        import urllib.request

        from social_research_probe.platforms.youtube.extract import _download_subtitle

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"raw json blob"

        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: _Resp())
        assert _download_subtitle("https://x", "json3") == "raw json blob"


def test_fetch_transcript_returns_none_when_yt_dlp_raises(monkeypatch):
    """Catches errors from yt_dlp.extract_info (network failures, geo blocks)."""
    import sys
    import types

    import social_research_probe.platforms.youtube.extract as ext

    class _BoomYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            raise RuntimeError("yt-dlp blew up")

    fake = types.ModuleType("yt_dlp")
    fake.YoutubeDL = _BoomYDL
    monkeypatch.setitem(sys.modules, "yt_dlp", fake)
    assert ext.fetch_transcript("https://x") is None


def test_strip_vtt_collapses_duplicate_lines():
    from social_research_probe.platforms.youtube.extract import _strip_vtt

    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n\n00:00:02.000 --> 00:00:03.000\nHello\n"
    assert _strip_vtt(vtt) == "Hello"
