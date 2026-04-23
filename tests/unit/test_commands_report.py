"""Tests for the report command helpers."""

from __future__ import annotations

import json

import pytest

from social_research_probe.commands import report as report_cmd
from social_research_probe.commands.report import _audio_report_enabled, _technology_logs_enabled
from social_research_probe.config import Config
from social_research_probe.errors import ValidationError


def test_audio_report_enabled_fallback(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(Config, "load", raise_exc)
    assert _audio_report_enabled() is True


def test_technology_logs_enabled_fallback(monkeypatch):
    def raise_exc(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(Config, "load", raise_exc)
    assert _technology_logs_enabled() is False


def test_run_raises_when_html_report_generation_is_disabled(monkeypatch, tmp_path):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps({"topic": "AI"}), encoding="utf-8")

    class _Cfg:
        def stage_enabled(self, name: str) -> bool:
            return True

        def service_enabled(self, name: str) -> bool:
            return name != "html_report"

        def technology_enabled(self, name: str) -> bool:
            return True

    monkeypatch.setattr(report_cmd.Config, "load", lambda data_dir: _Cfg())

    with pytest.raises(ValidationError, match="HTML report generation is disabled by config"):
        report_cmd.run(
            str(packet_path),
            None,
            None,
            None,
            str(tmp_path / "report.html"),
            data_dir=tmp_path,
        )


def test_run_skips_voicebox_profile_loading_when_voicebox_technology_disabled(
    monkeypatch, tmp_path
):
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps({"topic": "AI"}), encoding="utf-8")
    captured: dict[str, object] = {}

    class _Cfg:
        def stage_enabled(self, name: str) -> bool:
            return True

        def service_enabled(self, name: str) -> bool:
            return True

        def technology_enabled(self, name: str) -> bool:
            return name != "voicebox"

    def _fake_render_html(
        packet,
        *,
        charts_dir,
        data_dir,
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

    monkeypatch.setattr(report_cmd.Config, "load", lambda data_dir: _Cfg())
    monkeypatch.setattr(report_cmd, "_audio_report_enabled", lambda data_dir=None: False)
    monkeypatch.setattr(
        "social_research_probe.render.html._fetch_voicebox_profiles",
        lambda api_base: (_ for _ in ()).throw(AssertionError("voicebox profiles should not load")),
    )
    monkeypatch.setattr("social_research_probe.render.html.render_html", _fake_render_html)
    monkeypatch.setattr(
        "social_research_probe.render.html.serve_report_command", lambda dest: "cmd"
    )

    rc = report_cmd.run(
        str(packet_path),
        None,
        None,
        None,
        str(tmp_path / "report.html"),
        data_dir=tmp_path,
    )

    assert rc == 0
    assert captured["tts_profiles"] == []
    assert captured["tts_profile_name"] is None
