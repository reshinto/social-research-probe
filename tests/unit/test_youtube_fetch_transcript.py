"""Complementary tests for fetch_transcript and whisper diagnostic helpers.

The main fetch_transcript coverage lives in test_youtube_extract.py.
This file covers:
- _log_ytdlp_failure in whisper_transcript (bot-check hint + stderr logging)
- fetch_transcript graceful degradation with both API flags combined
"""

from __future__ import annotations

import social_research_probe.platforms.youtube.whisper_transcript as wt
from social_research_probe.technologies.media_fetch.yt_dlp import YtDlpFlag


class TestLogYtdlpFailure:
    def test_bot_check_hint_emitted_once(self, monkeypatch):
        """Bot-check hint fires at most once per process."""
        monkeypatch.setattr(wt, "_bot_hint_shown", False)
        logged: list[str] = []
        monkeypatch.setattr(wt, "log", logged.append)

        wt._log_ytdlp_failure("Sign in to confirm you're not a bot.")
        wt._log_ytdlp_failure("Sign in to confirm you're not a bot.")

        hint_lines = [m for m in logged if "bot-check" in m]
        assert len(hint_lines) == 1

    def test_non_bot_failure_logs_first_stderr_line(self, monkeypatch):
        """Non-bot-check stderr logs the first line of stderr output."""
        monkeypatch.setattr(wt, "_bot_hint_shown", False)
        logged: list[str] = []
        monkeypatch.setattr(wt, "log", logged.append)

        wt._log_ytdlp_failure("ERROR: network timeout\nsome other line")

        assert any("yt-dlp failed: ERROR: network timeout" in m for m in logged)

    def test_empty_stderr_logs_nothing(self, monkeypatch):
        """Empty stderr produces no log output."""
        logged: list[str] = []
        monkeypatch.setattr(wt, "log", logged.append)

        wt._log_ytdlp_failure("")

        assert logged == []

    def test_bot_hint_not_shown_after_non_bot_failure(self, monkeypatch):
        """Bot-check hint is still available after a non-bot failure."""
        monkeypatch.setattr(wt, "_bot_hint_shown", False)
        logged: list[str] = []
        monkeypatch.setattr(wt, "log", logged.append)

        wt._log_ytdlp_failure("ERROR: some other problem")
        wt._log_ytdlp_failure("Sign in to confirm you're not a bot.")

        hint_lines = [m for m in logged if "bot-check" in m]
        assert len(hint_lines) == 1

    def test_whitespace_only_stderr_logs_nothing(self, monkeypatch):
        """Stderr that is only whitespace produces no log output."""
        monkeypatch.setattr(wt, "_bot_hint_shown", False)
        logged: list[str] = []
        monkeypatch.setattr(wt, "log", logged.append)

        wt._log_ytdlp_failure("   \n\t  ")

        assert logged == []


class TestFetchTranscriptWhisperCookies:
    def test_cookies_file_arg_added_when_env_set(self, monkeypatch, tmp_path):
        """SRP_YTDLP_COOKIES_FILE adds --cookies to the yt-dlp command."""
        import subprocess
        import sys
        import types

        fake_whisper = types.SimpleNamespace(load_model=lambda name: object())
        monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

        cookie_file = str(tmp_path / "cookies.txt")
        monkeypatch.setenv("SRP_YTDLP_COOKIES_FILE", cookie_file)

        captured_cmd: list = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            result = subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="")
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)
        wt.fetch_transcript_whisper("https://www.youtube.com/watch?v=abc")

        assert YtDlpFlag.COOKIES in captured_cmd
        assert cookie_file in captured_cmd


class TestFetchTranscriptIntegration:
    def test_returns_none_when_api_unavailable(self, monkeypatch):
        """fetch_transcript returns None gracefully when youtube-transcript-api is absent."""
        import social_research_probe.platforms.youtube.extract as ext

        monkeypatch.setattr(ext, "_API_AVAILABLE", False)
        assert ext.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is None

    def test_returns_none_for_unknown_url_scheme(self, monkeypatch):
        """fetch_transcript returns None for a URL with no parseable video ID."""
        import social_research_probe.platforms.youtube.extract as ext

        monkeypatch.setattr(ext, "_API_AVAILABLE", True)
        assert ext.fetch_transcript("not-a-url-at-all") is None
