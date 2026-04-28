"""Tests for technologies.report_render.html.raw_html.youtube helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.technologies.report_render.html.raw_html import youtube as yt_html


@pytest.fixture
def isolated(tmp_path):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    cfg.voicebox = {"api_base": "http://x", "default_profile_name": "Mine"}
    cfg.debug = {"technology_logs_enabled": False}
    cfg.stage_enabled.return_value = True
    cfg.service_enabled.return_value = True
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield tmp_path


def test_default_voicebox_api_base(isolated):
    assert yt_html._default_voicebox_api_base() == "http://x"


def test_voicebox_api_base_env(monkeypatch, isolated):
    monkeypatch.setenv("SRP_VOICEBOX_API_BASE", "http://env/")
    assert yt_html._voicebox_api_base() == "http://env"


def test_display_path_under_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    p = tmp_path / "x"
    p.mkdir()
    out = yt_html._display_path(p)
    assert out.startswith("~/")


def test_display_path_outside_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    out = yt_html._display_path(tmp_path / "elsewhere")
    assert "/" in out


def test_serve_report_command():
    out = yt_html.serve_report_command(Path("/tmp/x.html"))
    assert "srp serve-report" in out


def test_voicebox_default_profile_name(monkeypatch):
    cfg = MagicMock()
    cfg.voicebox = {"default_profile_name": "Mine"}
    with patch.object(yt_html, "load_active_config", return_value=cfg, create=True):
        assert yt_html._voicebox_default_profile_name() == "Mine"


def test_voicebox_default_profile_name_exception(monkeypatch):
    with patch("social_research_probe.config.load_active_config", side_effect=RuntimeError):
        assert yt_html._voicebox_default_profile_name() == "Jarvis"


def test_normalize_voicebox_name():
    assert yt_html._normalize_voicebox_profile_name("  HE LLO  ") == "he llo"


def test_dedupe_voicebox_name_unique():
    seen: set[str] = set()
    assert yt_html._dedupe_voicebox_profile_name("Alice", seen) == "Alice"


def test_dedupe_voicebox_name_collision():
    seen = {"alice"}
    out = yt_html._dedupe_voicebox_profile_name("Alice", seen)
    assert out.startswith("Alice (")


def test_dedupe_voicebox_name_blank():
    seen: set[str] = set()
    assert yt_html._dedupe_voicebox_profile_name("", seen) == "Voicebox Profile"


def test_write_discovered_no_profiles(isolated):
    yt_html._write_discovered_voicebox_profile_names([])
    assert not (isolated / "voicebox_profiles.json").exists()


def test_write_discovered_writes(tmp_path, monkeypatch):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    with patch.object(yt_html, "load_active_config", return_value=cfg, create=True):
        yt_html._write_discovered_voicebox_profile_names(
            [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}, {"id": "3", "name": "A"}]
        )
        out = json.loads((tmp_path / "voicebox_profiles.json").read_text())
    assert out == ["A", "B"]


def test_select_voicebox_profile_empty():
    assert yt_html._select_voicebox_profile([], tts_profile_name="x") is None


def test_select_voicebox_profile_match():
    profiles = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
    assert yt_html._select_voicebox_profile(profiles, tts_profile_name="Bob")["name"] == "Bob"


def test_select_voicebox_profile_default_first():
    profiles = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
    assert yt_html._select_voicebox_profile(profiles, tts_profile_name=None)["name"] == "Alice"


def test_audio_report_enabled(isolated):
    assert yt_html._audio_report_enabled() is True


def test_audio_report_enabled_exception(monkeypatch):
    with patch("social_research_probe.config.load_active_config", side_effect=RuntimeError):
        assert yt_html._audio_report_enabled() is True


def test_technology_logs_enabled(isolated):
    assert yt_html._technology_logs_enabled() is False


def test_technology_logs_enabled_exception(monkeypatch):
    with patch("social_research_probe.config.load_active_config", side_effect=RuntimeError):
        assert yt_html._technology_logs_enabled() is False


def test_build_tts_voice_options_empty():
    out = yt_html._build_tts_voice_options([], None)
    assert "Choose voice" in out


def test_build_tts_voice_options_select_default():
    profiles = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
    out = yt_html._build_tts_voice_options(profiles, "Bob")
    assert "Bob" in out and "selected" in out


def test_markdown_to_voiceover_text():
    out = yt_html._markdown_to_voiceover_text("# Title\n- bullet *bold*\n[link](url)")
    assert "Title" in out and "bullet" in out and "url" not in out


def test_build_voiceover_empty():
    assert yt_html.build_voiceover_text({}) is None


def test_build_voiceover_basic():
    out = yt_html.build_voiceover_text(
        {
            "compiled_synthesis": "x",
            "opportunity_analysis": "y",
            "report_summary": "z",
        }
    )
    assert "Compiled synthesis" in out and "Opportunity analysis" in out


def test_fetch_voicebox_profiles_failure(monkeypatch):
    def boom(*a, **kw):
        raise OSError

    monkeypatch.setattr(yt_html.urllib.request, "urlopen", boom)
    assert yt_html._fetch_voicebox_profiles("http://x") == []


def test_fetch_voicebox_profiles_invalid_payload(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return b'"string"'

    def fake_urlopen(*a, **kw):
        return FakeResp()

    monkeypatch.setattr(yt_html.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(yt_html.json, "load", lambda r: "string")
    assert yt_html._fetch_voicebox_profiles("http://x") == []


def test_fetch_voicebox_profiles_list(monkeypatch):
    monkeypatch.setattr(
        yt_html.json,
        "load",
        lambda r: [{"id": "1", "name": "A"}, "skip", {"id": "1", "name": "dup"}],
    )

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return b""

    monkeypatch.setattr(yt_html.urllib.request, "urlopen", lambda *a, **kw: FakeResp())
    out = yt_html._fetch_voicebox_profiles("http://x")
    assert len(out) == 1


def test_fetch_voicebox_profiles_dict(monkeypatch):
    monkeypatch.setattr(
        yt_html.json,
        "load",
        lambda r: {"profiles": [{"id": "1", "name": "A"}]},
    )

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return b""

    monkeypatch.setattr(yt_html.urllib.request, "urlopen", lambda *a, **kw: FakeResp())
    out = yt_html._fetch_voicebox_profiles("http://x")
    assert out[0]["name"] == "A"


def test_prepare_voiceover_audio_no_profile():
    out = yt_html._prepare_voiceover_audio(
        {}, Path("/tmp/x.html"), tts_api_base="http://x", tts_profile=None
    )
    assert out == (None, None)


def test_prepare_voiceover_audio_no_text():
    out = yt_html._prepare_voiceover_audio(
        {},
        Path("/tmp/x.html"),
        tts_api_base="http://x",
        tts_profile={"id": "1", "name": "A"},
    )
    assert out == (None, None)


def test_prepare_voiceover_audios_empty():
    out = yt_html._prepare_voiceover_audios(
        {},
        Path("/tmp/x.html"),
        tts_api_base="http://x",
        tts_profiles=[],
        tts_profile_name=None,
    )
    assert out == {}


def test_prepared_audio_base():
    out = yt_html._prepared_audio_base(Path("/tmp/r.html"), "Profile Name!")
    assert "voicebox" in out.name


def test_render_html_smoke(isolated, monkeypatch):
    monkeypatch.setattr(yt_html, "_fetch_voicebox_profiles", lambda *a, **kw: [])
    report = {
        "topic": "ai",
        "platform": "youtube",
        "purpose_set": ["x"],
        "items_top_n": [],
        "stats_summary": {},
        "platform_engagement_summary": "",
        "evidence_summary": "",
        "chart_captions": [],
        "warnings": [],
    }
    out = yt_html.render_html(report)
    assert "<html" in out and "ai" in out


def test_write_html_runs_without_stage_or_service_gates(tmp_path):
    """HTML technology no longer gates on stage/service flags — caller's job."""
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    cfg.stage_enabled.return_value = False
    cfg.technology_enabled.return_value = False
    with patch.object(yt_html, "load_active_config", return_value=cfg, create=True):
        path = yt_html.write_html_report(
            {
                "topic": "x",
                "platform": "y",
                "purpose_set": [],
                "items_top_n": [],
                "stats_summary": {},
                "platform_engagement_summary": "",
                "evidence_summary": "",
                "chart_captions": [],
                "warnings": [],
            }
        )
    assert path.exists()


def test_write_html_success(isolated, monkeypatch):
    monkeypatch.setattr(yt_html, "_fetch_voicebox_profiles", lambda *a, **kw: [])
    monkeypatch.setattr(yt_html, "_prepare_voiceover_audios", lambda *a, **kw: {})
    report = {
        "topic": "ai topic",
        "platform": "youtube",
        "purpose_set": [],
        "items_top_n": [],
        "stats_summary": {},
        "platform_engagement_summary": "",
        "evidence_summary": "",
        "chart_captions": [],
        "warnings": [],
    }
    path = yt_html.write_html_report(report, prepare_voicebox_audio=False)
    assert path.exists() and path.suffix == ".html"
