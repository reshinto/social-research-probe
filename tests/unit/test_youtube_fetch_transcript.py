"""Tests for social_research_probe.platforms.youtube.extract.fetch_transcript.

Covers the yt_dlp path using a monkeypatched YoutubeDL, the ImportError
fallback, and the no-English-track case.
"""

from __future__ import annotations

import sys
import types

import social_research_probe.platforms.youtube.extract as yt_extract


class _FakeYDL:
    """Minimal yt_dlp.YoutubeDL stand-in."""

    def __init__(self, opts):
        self._opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def extract_info(self, url, download=False):
        return self._info

    @classmethod
    def returning(cls, info: dict):
        inst = object.__new__(cls)
        inst._info = info
        return inst


def _patch_yt_dlp(monkeypatch, ydl_instance):
    """Install a fake yt_dlp module that returns ydl_instance from YoutubeDL(...)."""
    fake_yt_dlp = types.ModuleType("yt_dlp")
    fake_yt_dlp.YoutubeDL = lambda opts: ydl_instance
    monkeypatch.setitem(sys.modules, "yt_dlp", fake_yt_dlp)


def test_fetch_transcript_returns_none_when_yt_dlp_missing(monkeypatch):
    """fetch_transcript returns None when yt_dlp is not installed."""
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=abc")
    assert result is None


def test_fetch_transcript_returns_none_when_no_english_track(monkeypatch):
    """fetch_transcript returns None when subtitles have no 'en' key."""
    ydl = _FakeYDL({})
    ydl._info = {"subtitles": {"fr": []}, "automatic_captions": {}}
    _patch_yt_dlp(monkeypatch, ydl)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=abc")
    assert result is None


def test_fetch_transcript_returns_text_from_subtitles(monkeypatch):
    """fetch_transcript joins subtitle data strings when 'en' subtitles are present."""
    ydl = _FakeYDL({})
    ydl._info = {
        "subtitles": {"en": [{"data": "Hello"}, {"data": " world"}]},
        "automatic_captions": {},
    }
    _patch_yt_dlp(monkeypatch, ydl)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=abc")
    assert result == "Hello\n world"


def test_fetch_transcript_falls_back_to_auto_captions(monkeypatch):
    """fetch_transcript uses automatic_captions when subtitles has no 'en' key."""
    ydl = _FakeYDL({})
    ydl._info = {
        "subtitles": {},
        "automatic_captions": {"en": [{"data": "Auto caption"}]},
    }
    _patch_yt_dlp(monkeypatch, ydl)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=abc")
    assert result == "Auto caption"


def test_fetch_transcript_skips_non_dict_entries(monkeypatch):
    """fetch_transcript skips subtitle entries that are not dicts."""
    ydl = _FakeYDL({})
    ydl._info = {
        "subtitles": {"en": ["not a dict", {"data": "valid"}]},
    }
    _patch_yt_dlp(monkeypatch, ydl)
    result = yt_extract.fetch_transcript("https://www.youtube.com/watch?v=abc")
    assert result == "valid"
