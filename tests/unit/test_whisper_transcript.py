"""Tests for platforms/youtube/whisper_transcript.py."""

from __future__ import annotations

import sys

from social_research_probe.platforms.youtube.whisper_transcript import (
    fetch_transcript_whisper,
)


def test_returns_none_when_whisper_not_installed(monkeypatch):
    """If openai-whisper is not importable, function returns None gracefully."""
    monkeypatch.setitem(sys.modules, "whisper", None)
    result = fetch_transcript_whisper("https://www.youtube.com/watch?v=test")
    assert result is None


def test_returns_none_when_yt_dlp_download_fails(monkeypatch, tmp_path):
    """When yt-dlp exits non-zero (download failure), return None."""
    import subprocess
    import types

    fake_whisper = types.ModuleType("whisper")
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    class _FailResult:
        returncode = 1
        stdout = ""
        stderr = "error"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _FailResult())
    result = fetch_transcript_whisper("https://www.youtube.com/watch?v=test")
    assert result is None


def test_returns_none_when_no_mp3_in_tmpdir(monkeypatch):
    """When yt-dlp succeeds but produces no mp3, return None."""
    import subprocess
    import types

    fake_whisper = types.ModuleType("whisper")
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    class _OkResult:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _OkResult())
    # tmpdir will be empty — no mp3 files
    result = fetch_transcript_whisper("https://www.youtube.com/watch?v=test")
    assert result is None


def test_returns_transcript_text_on_success(monkeypatch, tmp_path):
    """Full success path: yt-dlp produces mp3, whisper returns text."""
    import subprocess
    import types

    fake_whisper = types.ModuleType("whisper")

    class _FakeModel:
        def transcribe(self, path, **kwargs):
            return {"text": "  Transcribed content here.  "}

    fake_whisper.load_model = lambda name: _FakeModel()
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    class _OkResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *a, **kw):
        if "--extract-audio" in cmd:
            # Simulate yt-dlp writing an mp3 into the tmpdir
            output_template = next((c for c in cmd if "%(ext)s" in c), None)
            if output_template:
                import os

                tmpdir = os.path.dirname(output_template)
                open(os.path.join(tmpdir, "audio.mp3"), "w").close()
        return _OkResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = fetch_transcript_whisper("https://www.youtube.com/watch?v=test")
    assert result == "Transcribed content here."


def test_returns_none_when_whisper_returns_empty_text(monkeypatch):
    """If Whisper transcribes but returns empty text, return None."""
    import subprocess
    import types

    fake_whisper = types.ModuleType("whisper")

    class _FakeModel:
        def transcribe(self, path, **kwargs):
            return {"text": "   "}

    fake_whisper.load_model = lambda name: _FakeModel()
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    class _OkResult:
        returncode = 0

    def fake_run(cmd, *a, **kw):
        if "--extract-audio" in cmd:
            output_template = next((c for c in cmd if "%(ext)s" in c), None)
            if output_template:
                import os

                tmpdir = os.path.dirname(output_template)
                open(os.path.join(tmpdir, "audio.mp3"), "w").close()
        return _OkResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = fetch_transcript_whisper("https://www.youtube.com/watch?v=test")
    assert result is None
