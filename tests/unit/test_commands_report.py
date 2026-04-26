"""Tests for the report command helpers."""

from __future__ import annotations

import json

import pytest

from social_research_probe.commands import report as report_cmd
from social_research_probe.technologies.report_render.html.raw_html.youtube import (
    _audio_report_enabled,
    _technology_logs_enabled,
)
from social_research_probe.utils.core.errors import ValidationError


def test_audio_report_enabled_fallback(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.report_render.html.raw_html.youtube.load_active_config",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert _audio_report_enabled() is True


def test_technology_logs_enabled_fallback(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.report_render.html.raw_html.youtube.load_active_config",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert _technology_logs_enabled() is False


def test_run_raises_when_html_report_generation_is_disabled(monkeypatch, tmp_path, tmp_data_dir):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps({"topic": "AI"}), encoding="utf-8")

    class _Cfg:
        def stage_enabled(self, platform: str, name: str) -> bool:
            return True

        def service_enabled(self, name: str) -> bool:
            return name != "html"

        def technology_enabled(self, name: str) -> bool:
            return True

    monkeypatch.setattr(
        "social_research_probe.commands.report.load_active_config",
        lambda: _Cfg(),
    )

    with pytest.raises(ValidationError, match="HTML report generation is disabled by config"):
        report_cmd.run(
            str(packet_path),
            None,
            None,
            None,
            str(tmp_path / "report.html"),
        )


def test_run_skips_voicebox_profile_loading_when_voicebox_technology_disabled(
    monkeypatch, tmp_path, tmp_data_dir
):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps({"topic": "AI"}), encoding="utf-8")
    captured: dict[str, object] = {}

    class _Cfg:
        def stage_enabled(self, platform: str, name: str) -> bool:
            return True

        def service_enabled(self, name: str) -> bool:
            return True

        def technology_enabled(self, name: str) -> bool:
            return name != "voicebox"

    def _fake_render_html(
        packet,
        *,
        charts_dir,
        tts_api_base,
        tts_profile_name,
        tts_profiles,
        prepared_audio_src,
        prepared_audio_profile_name,
        prepared_audio_sources,
    ):
        captured["tts_profiles"] = tts_profiles
        captured["tts_profile_name"] = tts_profile_name
        return "<html></html>"

    _render_module = "social_research_probe.technologies.report_render.html.raw_html.youtube"
    monkeypatch.setattr(
        "social_research_probe.commands.report.load_active_config",
        lambda: _Cfg(),
    )
    monkeypatch.setattr(
        f"{_render_module}._audio_report_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        f"{_render_module}._fetch_voicebox_profiles",
        lambda api_base: (_ for _ in ()).throw(AssertionError("voicebox profiles should not load")),
    )
    monkeypatch.setattr(f"{_render_module}.render_html", _fake_render_html)
    monkeypatch.setattr(f"{_render_module}.serve_report_command", lambda dest: "cmd")

    rc = report_cmd.run(
        str(packet_path),
        None,
        None,
        None,
        str(tmp_path / "report.html"),
    )

    assert rc == 0
    assert captured["tts_profiles"] == []
    assert captured["tts_profile_name"] is None
