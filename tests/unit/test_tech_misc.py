"""Tests for misc tech: transcript_fetch, media_fetch, tts."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.technologies.media_fetch import youtube_api, yt_dlp
from social_research_probe.technologies.transcript_fetch import (
    whisper as whisper_mod,
)
from social_research_probe.technologies.transcript_fetch import (
    youtube_transcript_api as yt_api,
)
from social_research_probe.technologies.tts import mac_tts, voicebox
from social_research_probe.utils.core.errors import AdapterError


class TestYoutubeTranscriptApi:
    def test_extract_video_id_from_watch(self):
        assert yt_api._extract_video_id("https://youtube.com/watch?v=abcDEF12345") == "abcDEF12345"

    def test_extract_video_id_from_shortlink(self):
        assert yt_api._extract_video_id("https://youtu.be/abcDEF12345") == "abcDEF12345"

    def test_extract_video_id_none(self):
        assert yt_api._extract_video_id("https://example.com") is None

    def test_fake_test_transcript_disabled(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        assert yt_api._fake_test_transcript("watch?v=fake") is None

    def test_fake_test_transcript_enabled(self, monkeypatch):
        monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
        out = yt_api._fake_test_transcript("https://youtube.com/watch?v=fake")
        assert out and "transcript-token-1" in out

    def test_fake_test_transcript_wrong_url(self, monkeypatch):
        monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
        assert yt_api._fake_test_transcript("https://youtube.com/watch?v=real") is None

    def test_fetch_transcript_invalid_url(self, monkeypatch):
        monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
        assert yt_api.fetch_transcript("not a url") is None


class TestWhisper:
    def test_load_model_cached_calls_module(self):
        whisper_mod._MODEL_CACHE.clear()
        fake = MagicMock()
        fake.load_model.return_value = "model"
        m1 = whisper_mod._load_model_cached(fake, "base")
        m2 = whisper_mod._load_model_cached(fake, "base")
        assert m1 == "model" == m2
        assert fake.load_model.call_count == 1


class TestYtDlp:
    def test_log_failure_blank(self):
        yt_dlp._log_ytdlp_failure("")

    def test_log_failure_other(self):
        yt_dlp._log_ytdlp_failure("error: something")

    def test_log_failure_bot_check(self, monkeypatch):
        monkeypatch.setattr(yt_dlp, "_bot_hint_shown", False)
        yt_dlp._log_ytdlp_failure("Sign in to confirm you are not a bot")

    def test_download_audio_subprocess_failure(self, tmp_path, monkeypatch):
        result = MagicMock(returncode=1, stderr="boom")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert yt_dlp.download_audio("u", str(tmp_path)) is None

    def test_download_audio_no_mp3(self, tmp_path, monkeypatch):
        result = MagicMock(returncode=0, stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert yt_dlp.download_audio("u", str(tmp_path)) is None

    def test_download_audio_returns_mp3(self, tmp_path, monkeypatch):
        (tmp_path / "audio.mp3").write_text("x")
        result = MagicMock(returncode=0, stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        out = yt_dlp.download_audio("u", str(tmp_path))
        assert out and out.name == "audio.mp3"


class TestYoutubeApi:
    def test_resolve_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("SRP_YOUTUBE_API_KEY", "envkey")
        with patch("social_research_probe.commands.config.read_secret", return_value=None):
            assert youtube_api.resolve_youtube_api_key() == "envkey"

    def test_resolve_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
        with (
            patch("social_research_probe.commands.config.read_secret", return_value=None),
            pytest.raises(AdapterError),
        ):
            youtube_api.resolve_youtube_api_key()

    def test_items_from_response_handles_non_list(self):
        assert youtube_api._items_from_response({"items": "x"}) == []

    def test_items_from_response_filters_non_dict(self):
        assert youtube_api._items_from_response({"items": [{"a": 1}, "x"]}) == [{"a": 1}]


class TestMacTts:
    def test_list_voices_failure(self, monkeypatch):
        def boom(*a, **kw):
            raise FileNotFoundError

        monkeypatch.setattr(subprocess, "run", boom)
        assert mac_tts.list_voices() == []

    def test_list_voices_parsed(self, monkeypatch):
        result = MagicMock(stdout="Alex en_US #x\nFred en_US #y\n")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        assert mac_tts.list_voices() == ["Alex", "Fred"]


class TestVoicebox:
    def test_extension_for_content_type(self):
        assert voicebox._extension_for_content_type("audio/mpeg") == ".mp3"
        assert voicebox._extension_for_content_type("audio/wav") == ".wav"
        assert voicebox._extension_for_content_type("audio/x-wav") == ".wav"
        assert voicebox._extension_for_content_type("audio/ogg") == ".ogg"
        assert voicebox._extension_for_content_type("application/octet-stream") == ".bin"

    def test_get_default_profile(self, monkeypatch):
        with patch(
            "social_research_probe.technologies.tts.voicebox.read_runtime_secret",
            return_value=None,
        ):
            assert voicebox._get_default_profile() == "Jarvis"
