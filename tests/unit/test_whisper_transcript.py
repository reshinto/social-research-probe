"""Tests for platforms/youtube/whisper_transcript.py."""

from __future__ import annotations

import sys

from social_research_probe.platforms.youtube.whisper_transcript import (
    fetch_transcript_whisper,
)
from social_research_probe.technologies.media_fetch.yt_dlp import YtDlpFlag


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
        if YtDlpFlag.EXTRACT_AUDIO in cmd:
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
        if YtDlpFlag.EXTRACT_AUDIO in cmd:
            output_template = next((c for c in cmd if "%(ext)s" in c), None)
            if output_template:
                import os

                tmpdir = os.path.dirname(output_template)
                open(os.path.join(tmpdir, "audio.mp3"), "w").close()
        return _OkResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = fetch_transcript_whisper("https://www.youtube.com/watch?v=test")
    assert result is None


def test_cached_transcript_short_circuits_download_and_model(monkeypatch, tmp_path):
    """Second call for the same video hits the cache — no yt-dlp, no model load."""
    import subprocess
    import types

    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)

    fake_whisper = types.ModuleType("whisper")
    load_count = [0]

    class _FakeModel:
        def transcribe(self, path, **kwargs):
            return {"text": "Transcribed text."}

    def _load(name):
        load_count[0] += 1
        return _FakeModel()

    fake_whisper.load_model = _load
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    subprocess_calls = [0]

    class _OkResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *a, **kw):
        subprocess_calls[0] += 1
        if YtDlpFlag.EXTRACT_AUDIO in cmd:
            output_template = next((c for c in cmd if "%(ext)s" in c), None)
            if output_template:
                import os

                tmpdir = os.path.dirname(output_template)
                open(os.path.join(tmpdir, "audio.mp3"), "w").close()
        return _OkResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    first = fetch_transcript_whisper(url)
    second = fetch_transcript_whisper(url)

    assert first == second == "Transcribed text."
    assert subprocess_calls[0] == 1  # only first call downloads audio
    assert load_count[0] == 1  # model cached on first load


def test_model_is_loaded_once_across_multiple_invocations(monkeypatch):
    """Whisper model loading is expensive (10-15s); it must be reused across calls."""
    import subprocess
    import types

    load_count = [0]

    class _FakeModel:
        def transcribe(self, path, **kwargs):
            return {"text": "hello"}

    def _load_model(name):
        load_count[0] += 1
        return _FakeModel()

    fake_whisper = types.ModuleType("whisper")
    fake_whisper.load_model = _load_model
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    class _OkResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, *a, **kw):
        if YtDlpFlag.EXTRACT_AUDIO in cmd:
            output_template = next((c for c in cmd if "%(ext)s" in c), None)
            if output_template:
                import os

                tmpdir = os.path.dirname(output_template)
                open(os.path.join(tmpdir, "audio.mp3"), "w").close()
        return _OkResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    fetch_transcript_whisper("https://www.youtube.com/watch?v=a")
    fetch_transcript_whisper("https://www.youtube.com/watch?v=b")
    fetch_transcript_whisper("https://www.youtube.com/watch?v=c")

    assert load_count[0] == 1


def test_cookies_from_browser_flag_added_when_env_set(monkeypatch):
    """When SRP_YTDLP_BROWSER is set, --cookies-from-browser is passed to yt-dlp."""
    import subprocess
    import types

    fake_whisper = types.ModuleType("whisper")
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)
    monkeypatch.setenv("SRP_YTDLP_BROWSER", "safari")

    captured: list[list[str]] = []

    class _FailResult:
        returncode = 1
        stdout = ""
        stderr = ""

    def fake_run(cmd, **_kw):
        captured.append(cmd)
        return _FailResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    fetch_transcript_whisper("https://www.youtube.com/watch?v=test")

    assert captured, "subprocess.run was never called"
    assert YtDlpFlag.COOKIES_FROM_BROWSER in captured[0]
    assert "safari" in captured[0]
