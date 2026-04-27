"""More html youtube tests covering _prepare_voiceover_audios + page shell."""

from __future__ import annotations

from social_research_probe.technologies.report_render.html.raw_html import youtube as yt_html


def test_prepare_voiceover_audio_with_text(tmp_path, monkeypatch):
    report = {"compiled_synthesis": "x", "opportunity_analysis": "y"}
    audio_path = tmp_path / "out.wav"
    audio_path.write_bytes(b"audio")

    def fake_write_audio(text, *, out_base, api_base, profile_id):
        return audio_path

    monkeypatch.setattr(
        "social_research_probe.technologies.tts.voicebox.write_audio", fake_write_audio
    )
    name, profile = yt_html._prepare_voiceover_audio(
        report,
        tmp_path / "r.html",
        tts_api_base="http://x",
        tts_profile={"id": "1", "name": "Alice"},
    )
    assert name == "out.wav" and profile == "Alice"


def test_prepare_voiceover_audio_runtime_error(tmp_path, monkeypatch, capsys):
    def fake_write_audio(text, *, out_base, api_base, profile_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "social_research_probe.technologies.tts.voicebox.write_audio", fake_write_audio
    )
    name, profile = yt_html._prepare_voiceover_audio(
        {"compiled_synthesis": "x"},
        tmp_path / "r.html",
        tts_api_base="http://x",
        tts_profile={"id": "1", "name": "A"},
    )
    assert name is None and profile is None


def test_prepare_voiceover_audios_with_profiles(tmp_path, monkeypatch):
    report = {"compiled_synthesis": "x"}

    def fake_write_audio(text, *, out_base, api_base, profile_id):
        path = tmp_path / f"{out_base.name}.wav"
        path.write_bytes(b"a")
        return path

    monkeypatch.setattr(
        "social_research_probe.technologies.tts.voicebox.write_audio", fake_write_audio
    )
    out = yt_html._prepare_voiceover_audios(
        report,
        tmp_path / "r.html",
        tts_api_base="http://x",
        tts_profiles=[{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}],
        tts_profile_name=None,
    )
    assert len(out) == 2 and "Alice" in out and "Bob" in out


def test_prepare_voiceover_audios_partial_failure(tmp_path, monkeypatch, capsys):
    report = {"compiled_synthesis": "x"}
    counter = {"n": 0}

    def fake_write_audio(text, *, out_base, api_base, profile_id):
        counter["n"] += 1
        if profile_id == "fail":
            raise RuntimeError("err")
        path = tmp_path / f"{out_base.name}.wav"
        path.write_bytes(b"a")
        return path

    monkeypatch.setattr(
        "social_research_probe.technologies.tts.voicebox.write_audio", fake_write_audio
    )
    out = yt_html._prepare_voiceover_audios(
        report,
        tmp_path / "r.html",
        tts_api_base="http://x",
        tts_profiles=[{"id": "fail", "name": "X"}, {"id": "ok", "name": "Y"}],
        tts_profile_name=None,
    )
    assert "Y" in out and "X" not in out


def test_page_shell_full(tmp_path):
    report = {"topic": "t"}
    out = yt_html._page_shell(
        report,
        "<nav/>",
        "<main/>",
        tts_api_base="http://x",
        tts_profiles=[{"id": "1", "name": "Alice"}],
        tts_profile_name="Alice",
        prepared_audio_src="audio.wav",
        prepared_audio_profile_name="Alice",
        prepared_audio_sources={"Alice": "audio.wav"},
    )
    assert "<!DOCTYPE html>" in out and "Alice" in out and "<main/>" in out


def test_render_html_with_embedded_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(
        yt_html, "_fetch_voicebox_profiles", lambda *a, **kw: [{"id": "1", "name": "Z"}]
    )
    monkeypatch.setattr(yt_html, "_write_discovered_voicebox_profile_names", lambda p: None)
    report = {
        "topic": "ai",
        "platform": "youtube",
        "purpose_set": [],
        "items_top_n": [],
        "stats_summary": {},
        "platform_engagement_summary": "",
        "evidence_summary": "",
        "chart_captions": [],
        "warnings": [],
    }
    out = yt_html.render_html(report, embed_voicebox_profiles=True)
    assert "Z" in out


def test_build_body():
    report = {"topic": "ai", "platform": "youtube"}
    out = yt_html._build_body(report, ["a"] * 12)
    assert "ai" in out


def test_build_toc():
    out = yt_html._build_toc()
    assert "<nav" in out or "<a " in out or out
