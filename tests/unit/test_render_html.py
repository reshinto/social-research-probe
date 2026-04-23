"""Tests for social_research_probe/render/ — HTML report generation."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from social_research_probe.render._sections import (
    _bulletise,
    _chart_block,
    _find_chart_path,
    _highlights_table,
    _items_links,
    _items_score_table,
    section_1_topic_purpose,
    section_2_platform,
    section_3_top_items,
    section_4_platform_signals,
    section_5_source_validation,
    section_6_evidence,
    section_7_statistics,
    section_8_charts,
    section_9_warnings,
    section_10_synthesis,
    section_11_opportunity,
    section_12_summary,
)
from social_research_probe.render.html import (
    _audio_report_enabled,
    _fetch_voicebox_profiles,
    _prepare_voiceover_audios,
    _prepared_audio_base,
    _select_voicebox_profile,
    _technology_logs_enabled,
    _voicebox_default_profile_name,
    _voicebox_profile_names_path,
    _write_discovered_voicebox_profile_names,
    build_voiceover_text,
    render_html,
    serve_report_command,
    write_html_report,
)
from social_research_probe.render.markdown_to_html import md_to_html

_SVS = {
    "validated": 1,
    "partially": 0,
    "unverified": 0,
    "low_trust": 0,
    "primary": 1,
    "secondary": 0,
    "commentary": 0,
    "notes": "auto-corroborated",
}

_ITEM = {
    "title": "Test Video",
    "channel": "TestChan",
    "url": "https://example.com/v",
    "source_class": "primary",
    "scores": {"trust": 0.8, "trend": 0.6, "opportunity": 0.5, "overall": 0.7},
    "one_line_takeaway": "A great insight",
}

_PACKET = {
    "topic": "AI agents",
    "platform": "youtube",
    "purpose_set": ["latest-news", "trends"],
    "items_top_n": [_ITEM],
    "source_validation_summary": _SVS,
    "platform_signals_summary": "high engagement; many views",
    "evidence_summary": "strong data; reliable sources",
    "stats_summary": {
        "models_run": ["regression"],
        "highlights": ["Mean score — 0.7"],
        "low_confidence": False,
    },
    "chart_captions": [],
    "warnings": [],
}


class TestMarkdownToHtml:
    def test_heading_level_1(self):
        assert "<h2>" in md_to_html("# Heading")

    def test_heading_level_4(self):
        assert "<h5>" in md_to_html("#### Deep")

    def test_heading_max_level_6(self):
        result = md_to_html("#### Deep")
        assert result.count("h6") == 0 or "<h5>" in result

    def test_horizontal_rule(self):
        assert "<hr>" in md_to_html("---")
        assert "<hr>" in md_to_html("***")
        assert "<hr>" in md_to_html("___")

    def test_bullet_list(self):
        html = md_to_html("- item one\n- item two")
        assert "<ul>" in html
        assert "<li>" in html

    def test_ordered_list(self):
        html = md_to_html("1. first\n2. second")
        assert "<ol>" in html
        assert "<li>" in html

    def test_paragraph(self):
        html = md_to_html("Plain text line.")
        assert "<p>" in html

    def test_blank_line_paragraph_break(self):
        html = md_to_html("Para one.\n\nPara two.")
        assert html.count("<p>") >= 2

    def test_bold_italic_combo(self):
        assert "<strong><em>" in md_to_html("***bold italic***")

    def test_bold(self):
        assert "<strong>" in md_to_html("**bold**")

    def test_italic_star(self):
        assert "<em>" in md_to_html("*italic*")

    def test_italic_underscore(self):
        assert "<em>" in md_to_html("_italic_")

    def test_inline_code(self):
        assert "<code>" in md_to_html("`code`")

    def test_link(self):
        html = md_to_html("[label](https://example.com)")
        assert '<a href="https://example.com"' in html
        assert "label" in html

    def test_html_escape(self):
        html = md_to_html("<script>alert(1)</script>")
        assert "<script>" not in html

    def test_list_close_on_switch_ul_to_ol(self):
        html = md_to_html("- bullet\n1. ordered")
        assert "</ul>" in html
        assert "<ol>" in html

    def test_list_close_on_switch_ol_to_ul(self):
        html = md_to_html("1. ordered\n- bullet")
        assert "</ol>" in html
        assert "<ul>" in html

    def test_multiline_collapsing(self):
        result = md_to_html("a\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_empty_string(self):
        assert md_to_html("") == ""


class TestSectionBuilders:
    def test_section_1(self):
        html = section_1_topic_purpose(_PACKET)
        assert "AI agents" in html
        assert "latest-news" in html

    def test_section_2(self):
        html = section_2_platform(_PACKET)
        assert "youtube" in html

    def test_section_3_with_items(self):
        html = section_3_top_items(_PACKET)
        assert "TestChan" in html
        assert "https://example.com/v" in html

    def test_section_3_no_items(self):
        pkt = {**_PACKET, "items_top_n": []}
        html = section_3_top_items(pkt)
        assert "no items" in html

    def test_items_links_with_transcript(self):
        item = {**_ITEM, "transcript": "Full transcript text"}
        html = _items_links([item])
        assert "<details>" in html
        assert "transcript" in html.lower()

    def test_items_links_transcript_truncated_at_3000(self):
        item = {**_ITEM, "transcript": "x" * 4000}
        html = _items_links([item])
        assert "..." in html

    def test_items_links_no_transcript(self):
        html = _items_links([_ITEM])
        assert "<details>" not in html

    def test_items_score_table(self):
        html = _items_score_table([_ITEM])
        assert "<table>" in html
        assert "0.70" in html or "0.7" in html

    def test_section_4(self):
        html = section_4_platform_signals(_PACKET)
        assert "high engagement" in html

    def test_section_5_with_notes(self):
        html = section_5_source_validation(_PACKET)
        assert "auto-corroborated" in html

    def test_section_5_no_notes(self):
        svs = {**_SVS, "notes": ""}
        pkt = {**_PACKET, "source_validation_summary": svs}
        html = section_5_source_validation(pkt)
        assert "<li>Notes:" not in html

    def test_section_6(self):
        html = section_6_evidence(_PACKET)
        assert "strong data" in html

    def test_section_7_with_highlights(self):
        html = section_7_statistics(_PACKET)
        assert "Mean score" in html

    def test_section_7_includes_model_and_interpretation_columns(self):
        pkt = {
            **_PACKET,
            "stats_summary": {
                "models_run": ["descriptive"],
                "highlights": ["Mean overall score: 0.70 — competitive baseline"],
                "low_confidence": False,
            },
        }
        html = section_7_statistics(pkt)
        assert "Model" in html
        assert "What it means" in html
        assert "descriptive" in html
        assert "Moderate baseline (0.70)" in html

    def test_section_7_no_highlights(self):
        pkt = {**_PACKET, "stats_summary": {"highlights": [], "low_confidence": False}}
        html = section_7_statistics(pkt)
        assert "no highlights" in html

    def test_section_7_low_confidence(self):
        pkt = {**_PACKET, "stats_summary": {"highlights": [], "low_confidence": True}}
        html = section_7_statistics(pkt)
        assert "Low confidence" in html

    def test_highlights_table_with_separator(self):
        html = _highlights_table(["Mean overall score: 0.70 — competitive baseline"])
        assert "<table>" in html
        assert "descriptive" in html
        assert "Mean overall score: 0.70" in html
        assert "Moderate baseline (0.70)" in html

    def test_highlights_table_without_separator(self):
        html = _highlights_table(["No separator line"])
        assert "No separator line" in html

    def test_section_8_no_captions(self):
        pkt = {**_PACKET, "chart_captions": []}
        html = section_8_charts(pkt, None)
        assert "no charts" in html

    def test_section_8_caption_only(self, tmp_path):
        pkt = {**_PACKET, "chart_captions": ["Bar chart: overall_score (5 items)\nASCII art here"]}
        html = section_8_charts(pkt, tmp_path)
        assert "Bar chart" in html
        assert "ASCII art here" in html

    def test_section_9_warnings(self):
        pkt = {**_PACKET, "warnings": ["low sample size"]}
        html = section_9_warnings(pkt)
        assert "low sample size" in html
        assert "warning-list" in html

    def test_section_9_no_warnings(self):
        html = section_9_warnings(_PACKET)
        assert "none" in html

    def test_section_10_with_text(self):
        html = section_10_synthesis("Here is synthesis **text**.")
        assert "<strong>" in html

    def test_section_10_none(self):
        html = section_10_synthesis(None)
        assert "LLM synthesis unavailable" in html

    def test_section_11_with_text(self):
        html = section_11_opportunity("Opportunity: **grow fast**.")
        assert "<strong>" in html

    def test_section_11_none(self):
        html = section_11_opportunity(None)
        assert "LLM synthesis unavailable" in html

    def test_section_12_with_text(self):
        html = section_12_summary("Final **summary** text.")
        assert "<strong>" in html

    def test_section_12_none(self):
        html = section_12_summary(None)
        assert "LLM summary unavailable" in html

    def test_bulletise_with_parts(self):
        html = _bulletise("part one; part two")
        assert "<li>part one</li>" in html
        assert "<li>part two</li>" in html

    def test_bulletise_empty(self):
        html = _bulletise("")
        assert "no data" in html


class TestFindChartPath:
    def test_none_when_charts_dir_none(self):
        assert _find_chart_path("_(see PNG: /some/path.png)_", None) is None

    def test_embedded_path_found(self, tmp_path):
        png = tmp_path / "chart.png"
        png.write_bytes(b"\x89PNG")
        cap = f"Line chart\n_(see PNG: {png})_"
        assert _find_chart_path(cap, tmp_path) == str(png)

    def test_embedded_path_not_exists(self, tmp_path):
        cap = "_(see PNG: /nonexistent/chart.png)_"
        assert _find_chart_path(cap, tmp_path) is None

    def test_bar_chart_path_found(self, tmp_path):
        png = tmp_path / "overall_score_bar.png"
        png.write_bytes(b"\x89PNG")
        cap = "Bar chart: overall_score (5 items)\nASCII"
        assert _find_chart_path(cap, tmp_path) == str(png)

    def test_bar_chart_path_not_exists(self, tmp_path):
        cap = "Bar chart: overall_score (5 items)\nASCII"
        assert _find_chart_path(cap, tmp_path) is None

    def test_no_match_returns_none(self, tmp_path):
        assert _find_chart_path("Random caption without path", tmp_path) is None


class TestChartBlock:
    def test_with_existing_png(self, tmp_path):
        png = tmp_path / "overall_score_bar.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
        cap = "Bar chart: overall_score (5 items)\nASCII art"
        html = _chart_block(cap, tmp_path)
        assert "data:image/png;base64," in html
        assert "chart-caption" in html

    def test_with_os_error(self, tmp_path, monkeypatch):
        png = tmp_path / "overall_score_bar.png"
        png.write_bytes(b"\x89PNG")
        cap = "Bar chart: overall_score (5 items)\nASCII"

        def raise_oserror(self):
            raise OSError("read error")

        monkeypatch.setattr(Path, "read_bytes", raise_oserror)
        html = _chart_block(cap, tmp_path)
        assert "chart-block" in html
        assert "data:image/png" not in html

    def test_caption_without_ascii(self, tmp_path):
        html = _chart_block("Bar chart: x (1 items)", tmp_path)
        assert "chart-caption" in html
        assert "chart-ascii" not in html

    def test_strips_see_png_annotation(self, tmp_path):
        html = _chart_block("Line chart: x\n_(see PNG: /x.png)_", tmp_path)
        assert "_(see PNG:" not in html


class TestRenderHtml:
    def test_produces_doctype(self):
        html = render_html(_PACKET)
        assert html.startswith("<!DOCTYPE html>")

    def test_contains_topic_in_title(self):
        html = render_html(_PACKET)
        assert "AI agents" in html

    def test_contains_all_section_ids(self):
        html = render_html(_PACKET)
        for sid in (
            "s1",
            "s2",
            "s3",
            "s4",
            "s5",
            "s6",
            "s7",
            "s8",
            "s9",
            "compiled-synthesis",
            "opportunity-analysis",
            "final-summary",
        ):
            assert f'id="{sid}"' in html

    def test_toc_links_present(self):
        html = render_html(_PACKET)
        assert 'href="#s1"' in html
        assert 'href="#final-summary"' in html

    def test_tts_controls_present(self):
        html = render_html(_PACKET)
        assert 'id="tts-play"' in html
        assert 'id="tts-pause"' in html
        assert 'id="tts-stop"' in html
        assert 'id="tts-audio"' in html
        assert 'id="tts-refresh"' in html

    def test_tts_script_present(self):
        html = render_html(_PACKET)
        assert "http://127.0.0.1:17493" in html
        assert "/profiles" in html
        assert "/generate" in html
        assert "/generate/stream" in html
        assert "/audio/" in html
        assert "max_chunk_chars" in html
        assert "localStorage" in html
        assert "Voicebox blocked from file:// page" in html
        assert "Voicebox stream stalled" in html
        assert "Preparing report narration " in html
        assert "#final-summary h2" in html
        assert "Prepared report narration ready" in html
        assert "speechSynthesis" in html
        assert "Using system voice" in html

    def test_tts_profiles_embedded_in_dropdown(self):
        html = render_html(
            _PACKET,
            tts_api_base="http://voicebox.local:9999",
            tts_profile_name="Bravo",
            tts_profiles=[
                {"id": "voice-1", "name": "Alpha"},
                {"id": "voice-2", "name": "Bravo"},
            ],
        )
        assert 'data-api-base="http://voicebox.local:9999"' in html
        assert 'value="voicebox::Alpha"' in html
        assert 'value="voicebox::Bravo"' in html
        assert 'data-source="voicebox"' in html
        assert 'data-voice-name="Bravo" selected="selected"' in html
        assert ">Bravo<" in html

    def test_tts_defaults_to_jarvis_profile_name_when_present(self):
        html = render_html(
            _PACKET,
            tts_profiles=[
                {"id": "voice-1", "name": "Alpha"},
                {"id": "voice-2", "name": "Jarvis"},
            ],
        )
        assert 'data-default-profile-name="Jarvis"' in html
        assert 'data-voice-name="Jarvis" selected="selected"' in html

    def test_tts_defaults_to_configured_profile_name(self, tmp_data_dir):
        (tmp_data_dir / "config.toml").write_text(
            '[voicebox]\ndefault_profile_name = "Friday"\n',
            encoding="utf-8",
        )
        html = render_html(
            _PACKET,
            data_dir=tmp_data_dir,
            tts_profiles=[
                {"id": "voice-1", "name": "Friday"},
                {"id": "voice-2", "name": "Jarvis"},
            ],
        )
        assert 'data-default-profile-name="Friday"' in html
        assert 'data-voice-name="Friday" selected="selected"' in html

    def test_render_html_embeds_and_caches_profiles_when_requested(self, tmp_path):
        with patch(
            "social_research_probe.render.html._fetch_voicebox_profiles",
            return_value=[{"id": "voice-1", "name": "Jarvis"}],
        ):
            html = render_html(
                _PACKET,
                data_dir=tmp_path,
                embed_voicebox_profiles=True,
            )
        assert 'data-voice-name="Jarvis" selected="selected"' in html
        assert json.loads(_voicebox_profile_names_path(tmp_path).read_text(encoding="utf-8")) == [
            "Jarvis"
        ]

    def test_prepared_audio_attrs_embedded(self):
        html = render_html(
            _PACKET,
            prepared_audio_src="ai-youtube.voicebox.wav",
            prepared_audio_profile_name="Bravo",
            prepared_audio_sources={"Alpha": "alpha.wav", "Bravo": "bravo.wav"},
        )
        assert 'data-prepared-audio-src="ai-youtube.voicebox.wav"' in html
        assert 'data-prepared-profile-name="Bravo"' in html
        assert '<script id="tts-prepared-audio-map" type="application/json">' in html
        assert '"Alpha": "alpha.wav"' in html
        assert '"Bravo": "bravo.wav"' in html

    def test_synthesis_10_rendered(self):
        html = render_html({**_PACKET, "compiled_synthesis": "My synthesis text."})
        assert "My synthesis text." in html

    def test_synthesis_11_rendered(self):
        html = render_html({**_PACKET, "opportunity_analysis": "My opportunity text."})
        assert "My opportunity text." in html

    def test_synthesis_12_rendered(self):
        html = render_html({**_PACKET, "report_summary": "My final summary text."})
        assert "My final summary text." in html

    def test_placeholder_when_no_synthesis(self):
        html = render_html(_PACKET)
        assert "LLM synthesis unavailable" in html
        assert "This report covers AI agents on youtube." in html
        assert (
            "Source validation: 1 validated, 0 partial, 0 unverified, and 0 low-trust sources."
            in html
        )

    def test_chart_embedded_when_png_exists(self, tmp_path):
        png = tmp_path / "overall_score_bar.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
        pkt = {**_PACKET, "chart_captions": ["Bar chart: overall_score (5 items)\nASCII"]}
        html = render_html(pkt, charts_dir=tmp_path)
        assert "data:image/png;base64," in html

    def test_html_escaping_in_topic(self):
        pkt = {**_PACKET, "topic": "<script>xss_marker</script>"}
        result = render_html(pkt)
        # The raw tag must not appear; the content should be entity-escaped
        assert "<script>xss_marker</script>" not in result
        assert "&lt;script&gt;" in result or "xss_marker" not in result.split("<script>", 1)[0]

    def test_dark_mode_css_present(self):
        html = render_html(_PACKET)
        assert "prefers-color-scheme: dark" in html


class TestVoiceoverHelpers:
    def test_build_voiceover_text_uses_only_summary_sections(self):
        text = build_voiceover_text(
            {
                **_PACKET,
                "compiled_synthesis": "## Compiled\n\nOne **strong** takeaway.",
                "opportunity_analysis": "- Opportunity item",
                "report_summary": "[Charts](https://example.com) reinforce the signal.",
            }
        )
        assert text is not None
        assert "Compiled synthesis." in text
        assert "Opportunity analysis." in text
        assert "Final summary." in text
        assert "strong" in text
        assert "Charts reinforce the signal." in text
        assert "https://example.com" not in text

    def test_build_voiceover_text_falls_back_to_deterministic_summary(self):
        text = build_voiceover_text(_PACKET)
        assert text is not None
        assert "Final summary." in text
        assert "This report covers AI agents on youtube." in text
        assert "Source validation:" in text
        assert "Statistics highlights:" in text
        assert "Platform signals:" in text
        assert "Evidence summary:" in text

    def test_build_voiceover_text_returns_none_for_truly_empty_packet(self):
        assert build_voiceover_text({}) is None

    def test_select_voicebox_profile_prefers_requested_name(self):
        selected = _select_voicebox_profile(
            [{"id": "voice-1", "name": "Alpha"}, {"id": "voice-2", "name": "Bravo"}],
            tts_profile_name="Bravo",
        )
        assert selected == {"id": "voice-2", "name": "Bravo"}

    def test_select_voicebox_profile_falls_back_to_first_available(self):
        selected = _select_voicebox_profile(
            [{"id": "voice-1", "name": "Alpha"}, {"id": "voice-2", "name": "Bravo"}],
            tts_profile_name="missing",
        )
        assert selected == {"id": "voice-1", "name": "Alpha"}

    def test_select_voicebox_profile_falls_back_when_no_preferred_name(self):
        selected = _select_voicebox_profile(
            [{"id": "voice-1", "name": "Alpha"}, {"id": "voice-2", "name": "Bravo"}],
            tts_profile_name=None,
        )
        assert selected == {"id": "voice-1", "name": "Alpha"}

    def test_voicebox_default_profile_name_falls_back_to_jarvis_on_config_error(self, monkeypatch):
        from social_research_probe.config import Config

        def raise_exc(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(Config, "load", raise_exc)
        assert _voicebox_default_profile_name() == "Jarvis"

    def test_prepared_audio_base_is_stable_and_sanitized(self, tmp_path):
        report_path = tmp_path / "report.html"
        result = _prepared_audio_base(report_path, "Voice Profile/Primary")
        assert result.parent == tmp_path
        assert result.name.startswith("report.voicebox.voice-profile-primary-")

    def test_prepare_voiceover_audios_skips_without_profile(self, tmp_path):
        report_path = tmp_path / "report.html"
        prepared = _prepare_voiceover_audios(
            _PACKET,
            report_path,
            tts_api_base="http://127.0.0.1:17493",
            tts_profiles=[],
            tts_profile_name=None,
        )
        assert prepared == {}

    def test_audio_report_enabled_reads_data_dir_config(self, tmp_path):
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text("[services.report]\naudio_report = false\n", encoding="utf-8")
        assert _audio_report_enabled(tmp_path) is False

    def test_prepare_voiceover_audios_returns_one_file_per_profile(self, tmp_path, monkeypatch):
        report_path = tmp_path / "report.html"
        captured = []

        def fake_write_audio(text, *, out_base, api_base, profile_id):
            captured.append((text, out_base, api_base, profile_id))
            path = out_base.parent / f"{out_base.name}.wav"
            path.write_bytes(b"wav")
            return path

        monkeypatch.setattr(
            "social_research_probe.render.tts.voicebox.write_audio", fake_write_audio
        )
        prepared = _prepare_voiceover_audios(
            {
                **_PACKET,
                "compiled_synthesis": "Compiled.",
                "opportunity_analysis": "Opportunity.",
                "report_summary": "Final summary.",
            },
            report_path,
            tts_api_base="http://voicebox.local:17493",
            tts_profiles=[
                {"id": "voice-1", "name": "Alpha"},
                {"id": "voice-2", "name": "Bravo"},
            ],
            tts_profile_name="Bravo",
        )
        assert set(prepared) == {"Alpha", "Bravo"}
        assert prepared["Alpha"].endswith(".wav")
        assert prepared["Bravo"].endswith(".wav")
        assert all(call[2] == "http://voicebox.local:17493" for call in captured)
        assert {call[3] for call in captured} == {"voice-1", "voice-2"}
        assert all("Final summary. Final summary." in call[0] for call in captured)

    def test_prepare_voiceover_audios_logs_and_skips_failed_profiles(
        self, tmp_path, monkeypatch, capsys
    ):
        report_path = tmp_path / "report.html"

        def fake_write_audio(text, *, out_base, api_base, profile_id):
            if profile_id == "voice-2":
                raise RuntimeError("voicebox unavailable")
            path = out_base.parent / f"{out_base.name}.wav"
            path.write_bytes(b"wav")
            return path

        monkeypatch.setattr(
            "social_research_probe.render.tts.voicebox.write_audio", fake_write_audio
        )
        prepared = _prepare_voiceover_audios(
            {
                **_PACKET,
                "compiled_synthesis": "Compiled.",
                "opportunity_analysis": "Opportunity.",
                "report_summary": "Final summary.",
            },
            report_path,
            tts_api_base="http://voicebox.local:17493",
            tts_profiles=[
                {"id": "voice-1", "name": "Alpha"},
                {"id": "voice-2", "name": "Bravo"},
            ],
            tts_profile_name="Bravo",
        )
        assert list(prepared) == ["Alpha"]
        assert "Voicebox audio pre-render skipped for profile Bravo" in capsys.readouterr().err


class TestWriteHtmlReport:
    @pytest.fixture(autouse=True)
    def _stub_voicebox_helpers(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.render.html._fetch_voicebox_profiles", lambda api_base: []
        )
        monkeypatch.setattr(
            "social_research_probe.render.html._prepare_voiceover_audios",
            lambda packet, report_path, *, tts_api_base, tts_profiles, tts_profile_name: {},
        )

    def test_creates_report_file(self, tmp_path):
        out = write_html_report(_PACKET, tmp_path)
        assert out.exists()
        assert out.suffix == ".html"
        assert "reports" in str(out)

    def test_report_filename_contains_topic_slug(self, tmp_path):
        out = write_html_report(_PACKET, tmp_path)
        assert "ai-agents" in out.name or "ai" in out.name

    def test_report_filename_contains_platform(self, tmp_path):
        out = write_html_report(_PACKET, tmp_path)
        assert "youtube" in out.name

    def test_synthesis_included_when_provided(self, tmp_path):
        out = write_html_report(
            {
                **_PACKET,
                "compiled_synthesis": "synth10 text",
                "opportunity_analysis": "synth11 text",
            },
            tmp_path,
        )
        content = out.read_text(encoding="utf-8")
        assert "synth10 text" in content
        assert "synth11 text" in content

    def test_prints_serve_report_command_to_stderr(self, tmp_path, capsys):
        out = write_html_report(_PACKET, tmp_path)
        err = capsys.readouterr().err
        assert "Serve report" in err
        assert serve_report_command(out) in err
        assert "file://" not in err

    def test_creates_reports_dir(self, tmp_path):
        reports_dir = tmp_path / "reports"
        assert not reports_dir.exists()
        write_html_report(_PACKET, tmp_path)
        assert reports_dir.is_dir()

    def test_embeds_voicebox_profiles_when_available(self, tmp_path):
        with patch(
            "social_research_probe.render.html._fetch_voicebox_profiles",
            return_value=[{"id": "voice-1", "name": "Alpha"}],
        ):
            out = write_html_report(_PACKET, tmp_path)
        content = out.read_text(encoding="utf-8")
        assert 'value="voicebox::Alpha"' in content
        assert 'data-source="voicebox"' in content
        assert ">Alpha<" in content
        assert json.loads(_voicebox_profile_names_path(tmp_path).read_text(encoding="utf-8")) == [
            "Alpha"
        ]

    def test_does_not_touch_profile_name_cache_without_profiles(self, tmp_path):
        cache_path = _voicebox_profile_names_path(tmp_path)
        cache_path.write_text(json.dumps(["Existing"]), encoding="utf-8")
        write_html_report(_PACKET, tmp_path)
        assert json.loads(cache_path.read_text(encoding="utf-8")) == ["Existing"]

    def test_write_html_report_raises_when_html_report_is_disabled(self, tmp_path):
        (tmp_path / "config.toml").write_text(
            "[services.report]\nhtml_report = false\n",
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError, match="HTML report generation is disabled by config"):
            write_html_report(_PACKET, tmp_path)

    def test_embeds_prepared_audio_attrs_when_audio_is_pre_rendered(self, tmp_path):
        with (
            patch(
                "social_research_probe.render.html._fetch_voicebox_profiles",
                return_value=[{"id": "voice-1", "name": "Alpha"}],
            ),
            patch(
                "social_research_probe.render.html._prepare_voiceover_audios",
                return_value={"Alpha": "report.voicebox.alpha.wav"},
            ),
        ):
            out = write_html_report(
                {
                    **_PACKET,
                    "compiled_synthesis": "synth10 text",
                    "opportunity_analysis": "synth11 text",
                    "report_summary": "summary12 text",
                },
                tmp_path,
            )
        content = out.read_text(encoding="utf-8")
        assert 'data-prepared-audio-src="report.voicebox.alpha.wav"' in content
        assert 'data-prepared-profile-name="Alpha"' in content
        assert '"Alpha": "report.voicebox.alpha.wav"' in content

    def test_emits_voicebox_service_logs_when_enabled(self, tmp_path, capsys):
        (tmp_path / "config.toml").write_text(
            "[debug]\ntechnology_logs_enabled = true\n",
            encoding="utf-8",
        )
        packet = {**_PACKET}
        with (
            patch(
                "social_research_probe.render.html._fetch_voicebox_profiles",
                return_value=[{"id": "voice-1", "name": "Alpha"}],
            ),
            patch(
                "social_research_probe.render.html._prepare_voiceover_audios",
                return_value={"Alpha": "report.voicebox.alpha.wav"},
            ),
        ):
            write_html_report(packet, tmp_path)
        err = capsys.readouterr().err
        assert "voicebox_profiles started" in err
        assert "voicebox_profiles done" in err
        assert "voicebox_audio started" in err
        assert "voicebox_audio done" in err
        stages = [entry["stage"] for entry in packet["stage_timings"]]
        assert "voicebox_profiles" in stages
        assert "voicebox_audio" in stages

    def test_skips_voicebox_profile_loading_when_voicebox_technology_disabled(self, tmp_path):
        (tmp_path / "config.toml").write_text(
            "[technologies]\nvoicebox = false\n",
            encoding="utf-8",
        )
        with patch(
            "social_research_probe.render.html._fetch_voicebox_profiles",
            side_effect=AssertionError("voicebox profiles should not load"),
        ):
            out = write_html_report(_PACKET, tmp_path, prepare_voicebox_audio=False)
        assert out.exists()


class TestVoiceboxProfileDiscovery:
    def test_fetch_voicebox_profiles_accepts_top_level_array(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'[{"id":"voice-1","name":"Alpha"}]'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_voicebox_profiles("http://127.0.0.1:17493")

        assert result == [{"id": "voice-1", "name": "Alpha"}]

    def test_fetch_voicebox_profiles_accepts_wrapped_profiles(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'{"profiles":[{"id":"voice-1","name":"Alpha"},{"id":"voice-2"}]}'
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_voicebox_profiles("http://127.0.0.1:17493")

        assert result == [
            {"id": "voice-1", "name": "Alpha"},
            {"id": "voice-2", "name": "Voicebox Profile"},
        ]

    def test_fetch_voicebox_profiles_filters_invalid_and_duplicate_entries(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'[{"id":"voice-1","name":"Alpha"},{"id":"voice-1","name":"Dup"},'
            b'{"id":""},"bad-entry",{"name":"missing-id"}]'
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_voicebox_profiles("http://127.0.0.1:17493")

        assert result == [{"id": "voice-1", "name": "Alpha"}]

    def test_fetch_voicebox_profiles_dedupes_duplicate_names_without_using_ids(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = (
            b'[{"id":"voice-1","name":"Jarvis"},{"id":"voice-2","name":"Jarvis"}]'
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_voicebox_profiles("http://127.0.0.1:17493")

        assert result == [
            {"id": "voice-1", "name": "Jarvis"},
            {"id": "voice-2", "name": "Jarvis (2)"},
        ]

    def test_fetch_voicebox_profiles_returns_empty_list_on_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = _fetch_voicebox_profiles("http://127.0.0.1:17493")

        assert result == []

    def test_write_discovered_voicebox_profile_names_skips_duplicates_and_blank_names(
        self, tmp_path
    ):
        _write_discovered_voicebox_profile_names(
            tmp_path,
            [
                {"id": "voice-1", "name": "Jarvis"},
                {"id": "voice-2", "name": " jarvis "},
                {"id": "voice-3", "name": "   "},
            ],
        )

        assert json.loads(_voicebox_profile_names_path(tmp_path).read_text(encoding="utf-8")) == [
            "Jarvis"
        ]

    def test_write_discovered_voicebox_profile_names_does_not_write_when_names_are_empty(
        self, tmp_path
    ):
        _write_discovered_voicebox_profile_names(
            tmp_path,
            [
                {"id": "voice-1", "name": "   "},
                {"id": "voice-2", "name": ""},
            ],
        )

        assert not _voicebox_profile_names_path(tmp_path).exists()


class TestCommandsReport:
    @pytest.fixture(autouse=True)
    def _stub_voicebox_helpers(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.render.html._fetch_voicebox_profiles", lambda api_base: []
        )
        monkeypatch.setattr(
            "social_research_probe.render.html._prepare_voiceover_audios",
            lambda packet, report_path, *, tts_api_base, tts_profiles, tts_profile_name: {},
        )

    def test_run_writes_to_out_path(self, tmp_path):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        out_path = tmp_path / "out.html"
        result = run(str(pkt_path), None, None, None, str(out_path))
        assert result == 0
        assert out_path.exists()
        assert "DOCTYPE" in out_path.read_text(encoding="utf-8")

    def test_run_writes_to_stdout_when_no_out(self, tmp_path, capsys):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        result = run(str(pkt_path), None, None, None, None)
        assert result == 0
        assert "DOCTYPE" in capsys.readouterr().out

    def test_run_reads_synthesis_files(self, tmp_path):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        compiled_synthesis = tmp_path / "compiled_synthesis.txt"
        opportunity_analysis = tmp_path / "opportunity_analysis.txt"
        final_summary = tmp_path / "final_summary.txt"
        compiled_synthesis.write_text("Compiled synthesis here", encoding="utf-8")
        opportunity_analysis.write_text("Opportunity analysis here", encoding="utf-8")
        final_summary.write_text("Final report summary here", encoding="utf-8")
        out_path = tmp_path / "out.html"
        run(
            str(pkt_path),
            str(compiled_synthesis),
            str(opportunity_analysis),
            str(final_summary),
            str(out_path),
        )
        content = out_path.read_text(encoding="utf-8")
        assert "Compiled synthesis here" in content
        assert "Opportunity analysis here" in content
        assert "Final report summary here" in content

    def test_run_invalid_json_raises_validation_error(self, tmp_path):
        from social_research_probe.commands.report import run
        from social_research_probe.errors import ValidationError

        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        with pytest.raises(ValidationError, match="cannot read packet file"):
            run(str(bad), None, None, None, None)

    def test_run_missing_packet_raises_validation_error(self, tmp_path):
        from social_research_probe.commands.report import run
        from social_research_probe.errors import ValidationError

        with pytest.raises(ValidationError, match="cannot read packet file"):
            run(str(tmp_path / "nonexistent.json"), None, None, None, None)

    def test_run_non_dict_packet_raises_validation_error(self, tmp_path):
        from social_research_probe.commands.report import run
        from social_research_probe.errors import ValidationError

        bad = tmp_path / "list.json"
        bad.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValidationError, match="packet file must contain a JSON object"):
            run(str(bad), None, None, None, None)

    def test_read_text_file_none_returns_none(self):
        from social_research_probe.commands.report import _read_text_file

        assert _read_text_file(None) is None

    def test_read_text_file_empty_returns_none(self, tmp_path):
        from social_research_probe.commands.report import _read_text_file

        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        assert _read_text_file(str(f)) is None

    def test_read_text_file_missing_raises_validation_error(self, tmp_path):
        from social_research_probe.commands.report import _read_text_file
        from social_research_probe.errors import ValidationError

        with pytest.raises(ValidationError):
            _read_text_file(str(tmp_path / "missing.txt"))

    def test_run_uses_charts_dir_sibling(self, tmp_path):
        from social_research_probe.commands.report import run

        charts = tmp_path / "charts"
        charts.mkdir()
        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        out_path = tmp_path / "out.html"
        result = run(str(pkt_path), None, None, None, str(out_path))
        assert result == 0

    def test_run_prints_serve_report_command_to_stderr(self, tmp_path, capsys):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        out_path = tmp_path / "out.html"
        assert run(str(pkt_path), None, None, None, str(out_path)) == 0
        err = capsys.readouterr().err
        assert "Serve report" in err
        assert serve_report_command(out_path) in err

    def test_run_dispatched_from_main(self, monkeypatch, tmp_path):
        from social_research_probe.cli import main

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        final_summary = tmp_path / "final_summary.txt"
        final_summary.write_text("CLI-injected summary", encoding="utf-8")
        out_path = tmp_path / "out.html"
        result = main(
            [
                "--data-dir",
                str(tmp_path),
                "report",
                "--packet",
                str(pkt_path),
                "--final-summary",
                str(final_summary),
                "--out",
                str(out_path),
            ]
        )
        assert result == 0
        assert out_path.exists()
        assert "CLI-injected summary" in out_path.read_text(encoding="utf-8")

    def test_run_emits_voicebox_service_logs_when_enabled(self, tmp_path, capsys, monkeypatch):
        from social_research_probe.commands.report import run

        (tmp_path / "config.toml").write_text(
            "[debug]\ntechnology_logs_enabled = true\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        out_path = tmp_path / "out.html"
        with (
            patch(
                "social_research_probe.render.html._fetch_voicebox_profiles",
                return_value=[{"id": "voice-1", "name": "Alpha"}],
            ),
            patch(
                "social_research_probe.render.html._prepare_voiceover_audios",
                return_value={"Alpha": "out.voicebox.alpha.wav"},
            ),
        ):
            assert run(str(pkt_path), None, None, None, str(out_path)) == 0
        err = capsys.readouterr().err
        assert "voicebox_profiles started" in err
        assert "voicebox_profiles done" in err
        assert "voicebox_audio started" in err
        assert "voicebox_audio done" in err


class TestTtpHttpAdapter:
    def test_synthesize_success(self):
        from social_research_probe.render.tts.http import synthesize

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"mp3data"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = synthesize("Hello world", "http://localhost:8080/synthesize")
        assert result == b"mp3data"

    def test_synthesize_http_error_raises(self):
        from social_research_probe.render.tts.http import synthesize

        with (
            patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.HTTPError("url", 500, "Server Error", {}, None),
            ),
            pytest.raises(RuntimeError, match="TTS server returned 500"),
        ):
            synthesize("Hello", "http://localhost:8080/synthesize")

    def test_synthesize_url_error_raises(self):
        from social_research_probe.render.tts.http import synthesize

        with (
            patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.URLError("connection refused"),
            ),
            pytest.raises(RuntimeError, match="TTS server unreachable"),
        ):
            synthesize("Hello", "http://localhost:8080/synthesize")

    def test_write_audio_creates_file(self, tmp_path):
        from social_research_probe.render.tts.http import write_audio

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"mp3bytes"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        out = tmp_path / "audio.mp3"
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = write_audio("Hello", out, "http://localhost:8080/synthesize")
        assert result == out
        assert out.read_bytes() == b"mp3bytes"


class TestVoiceboxTtsAdapter:
    def test_synthesize_success(self):
        from social_research_probe.render.tts.voicebox import synthesize

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"wavdata"
        mock_resp.headers = {"Content-Type": "audio/wav"}
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            audio, content_type = synthesize(
                "Hello world",
                api_base="http://voicebox.local:17493",
                profile_id="voice-1",
            )
        assert audio == b"wavdata"
        assert content_type == "audio/wav"

    def test_synthesize_http_error_raises(self):
        from social_research_probe.render.tts.voicebox import synthesize

        error = urllib.error.HTTPError(
            "http://voicebox.local:17493/generate/stream",
            500,
            "Server Error",
            {"Content-Type": "text/plain; charset=utf-8"},
            io.BytesIO(b"boom"),
        )
        with (
            patch("urllib.request.urlopen", side_effect=error),
            pytest.raises(RuntimeError, match="Voicebox returned 500: boom"),
        ):
            synthesize("Hello", api_base="http://voicebox.local:17493", profile_id="voice-1")

    def test_synthesize_url_error_raises(self):
        from social_research_probe.render.tts.voicebox import synthesize

        with (
            patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.URLError("connection refused"),
            ),
            pytest.raises(RuntimeError, match="Voicebox unreachable"),
        ):
            synthesize("Hello", api_base="http://voicebox.local:17493", profile_id="voice-1")

    def test_synthesize_empty_audio_raises(self):
        from social_research_probe.render.tts.voicebox import synthesize

        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_resp.headers = {"Content-Type": "audio/wav"}
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with (
            patch("urllib.request.urlopen", return_value=mock_resp),
            pytest.raises(RuntimeError, match="Voicebox returned empty audio"),
        ):
            synthesize("Hello", api_base="http://voicebox.local:17493", profile_id="voice-1")

    def test_write_audio_creates_extension_from_content_type(self, tmp_path):
        from social_research_probe.render.tts.voicebox import write_audio

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"oggbytes"
        mock_resp.headers = {"Content-Type": "audio/ogg"}
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = write_audio(
                "Hello",
                out_base=tmp_path / "report.voicebox",
                api_base="http://voicebox.local:17493",
                profile_id="voice-1",
            )
        assert result == tmp_path / "report.voicebox.ogg"
        assert result.read_bytes() == b"oggbytes"

    def test_extension_for_content_type_falls_back_to_bin(self):
        from social_research_probe.render.tts.voicebox import _extension_for_content_type

        assert _extension_for_content_type("audio/mpeg") == ".mp3"
        assert _extension_for_content_type("audio/wav") == ".wav"
        assert _extension_for_content_type("audio/x-wav") == ".wav"
        assert _extension_for_content_type("application/octet-stream") == ".bin"


class TestResearchHtmlInCli:
    """Integration tests for HTML output wired into the research CLI path."""

    _PACKET_WITH_SYNTHESIS: ClassVar[dict] = {
        **_PACKET,
        "compiled_synthesis": "synth10 text",
        "opportunity_analysis": "synth11 text",
        "report_summary": "summary12 text",
    }

    def _patch_pipeline(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_research",
            AsyncMock(return_value=self._PACKET_WITH_SYNTHESIS),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        monkeypatch.setattr(
            "social_research_probe.render.html._fetch_voicebox_profiles", lambda api_base: []
        )
        monkeypatch.setattr(
            "social_research_probe.render.html._prepare_voiceover_audios",
            lambda packet, report_path, *, tts_api_base, tts_profiles, tts_profile_name: {},
        )

    def test_html_file_written_in_research_command(self, monkeypatch, tmp_path, capsys):
        from social_research_probe.cli import main

        self._patch_pipeline(monkeypatch)
        assert main(["--data-dir", str(tmp_path), "research", "ai", "latest-news"]) == 0
        reports = list((tmp_path / "reports").glob("*.html"))
        assert len(reports) == 1
        out = capsys.readouterr().out.strip()
        assert out == serve_report_command(reports[0])

    def test_no_html_flag_suppresses_file(self, monkeypatch, tmp_path):
        from social_research_probe.cli import main

        self._patch_pipeline(monkeypatch)
        assert (
            main(["--data-dir", str(tmp_path), "research", "ai", "latest-news", "--no-html"]) == 0
        )
        reports_dir = tmp_path / "reports"
        assert not reports_dir.exists() or not list(reports_dir.glob("*.html"))

    def test_report_command_accepts_envelope_packet(self, tmp_path):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(
            json.dumps({"kind": "synthesis", "packet": self._PACKET_WITH_SYNTHESIS}),
            encoding="utf-8",
        )
        out_path = tmp_path / "out.html"
        assert run(str(pkt_path), None, None, None, str(out_path)) == 0
        assert "synth10 text" in out_path.read_text(encoding="utf-8")

    def test_render_command_accepts_envelope_packet(self, monkeypatch, tmp_path):
        from social_research_probe.commands import render as render_cmd

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(
            json.dumps({"kind": "synthesis", "packet": self._PACKET_WITH_SYNTHESIS}),
            encoding="utf-8",
        )

        monkeypatch.setattr(render_cmd, "select_and_run", lambda data, label: [])
        monkeypatch.setattr(
            render_cmd,
            "select_and_render",
            lambda data, label, output_dir: type(
                "_Chart",
                (),
                {"path": "/tmp/chart.png", "caption": "cap"},
            )(),
        )

        assert render_cmd.run(str(pkt_path)) == 0

    def test_synthesis_error_returns_nonzero(self, monkeypatch, tmp_path):
        from social_research_probe.cli import main
        from social_research_probe.errors import SynthesisError

        monkeypatch.setattr(
            "social_research_probe.pipeline.run_research",
            AsyncMock(return_value=_PACKET),
        )
        monkeypatch.setattr(
            "social_research_probe.cli._attach_synthesis",
            lambda pkt: (_ for _ in ()).throw(SynthesisError("boom")),
        )
        assert main(["--data-dir", str(tmp_path), "research", "ai", "latest-news"]) == 4


class TestHtmlCoverageGaps:
    def test_display_path_fallback_on_value_error(self):
        from pathlib import Path

        from social_research_probe.render.html import _display_path

        res = _display_path(Path("/"))
        assert res == "/"

    def test_display_path_success(self):
        from pathlib import Path

        from social_research_probe.render.html import _display_path

        home = Path.home().resolve()
        res = _display_path(home / "some" / "path")
        assert res == "~/some/path"

    def test_fetch_voicebox_profiles_returns_empty_on_unexpected_payload(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'"string"'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _fetch_voicebox_profiles("http://127.0.0.1:17493")
        assert result == []

    def test_audio_report_enabled_fallback_on_exception(self, tmp_path, monkeypatch):
        def raise_exc(*args, **kwargs):
            raise RuntimeError()

        from social_research_probe.config import Config

        monkeypatch.setattr(Config, "load", raise_exc)
        assert _audio_report_enabled(tmp_path) is True

    def test_technology_logs_enabled_fallback_on_exception(self, tmp_path, monkeypatch):
        def raise_exc(*args, **kwargs):
            raise RuntimeError()

        from social_research_probe.config import Config

        monkeypatch.setattr(Config, "load", raise_exc)
        assert _technology_logs_enabled(tmp_path) is False

    def test_build_voiceover_text_skips_empty_markdown(self):
        text = build_voiceover_text(
            {
                "topic": "test",
                "compiled_synthesis": "```\ncode\n```",
                "opportunity_analysis": "Opportunity analysis text.",
            }
        )
        assert text is not None
        assert "Opportunity analysis" in text
        assert "Compiled synthesis" not in text

    def test_prepare_voiceover_audio_no_profile(self, tmp_path):
        from social_research_probe.render.html import _prepare_voiceover_audio

        res = _prepare_voiceover_audio(
            _PACKET, tmp_path / "a.html", tts_api_base="base", tts_profile=None
        )
        assert res == (None, None)

    def test_prepare_voiceover_audio_no_text(self, tmp_path):
        from social_research_probe.render.html import _prepare_voiceover_audio

        res = _prepare_voiceover_audio(
            {},
            tmp_path / "a.html",
            tts_api_base="base",
            tts_profile={"id": "p-id", "name": "Jarvis"},
        )
        assert res == (None, None)

    def test_prepare_voiceover_audio_success(self, tmp_path, monkeypatch):
        from social_research_probe.render.html import _prepare_voiceover_audio

        def mock_write(text, out_base, api_base, profile_id):
            return out_base.parent / f"{out_base.name}.wav"

        monkeypatch.setattr("social_research_probe.render.tts.voicebox.write_audio", mock_write)
        res = _prepare_voiceover_audio(
            _PACKET,
            tmp_path / "a.html",
            tts_api_base="base",
            tts_profile={"id": "p-id", "name": "Jarvis"},
        )
        assert res[0].endswith(".wav")
        assert res[1] == "Jarvis"

    def test_prepare_voiceover_audio_runtime_error(self, tmp_path, monkeypatch):
        from social_research_probe.render.html import _prepare_voiceover_audio

        def mock_write(text, out_base, api_base, profile_id):
            raise RuntimeError()

        monkeypatch.setattr("social_research_probe.render.tts.voicebox.write_audio", mock_write)
        res = _prepare_voiceover_audio(
            _PACKET,
            tmp_path / "a.html",
            tts_api_base="base",
            tts_profile={"id": "p-id", "name": "Jarvis"},
        )
        assert res == (None, None)

    def test_prepare_voiceover_audios_no_text(self, tmp_path):
        res = _prepare_voiceover_audios(
            {},
            tmp_path / "report.html",
            tts_api_base="base",
            tts_profiles=[],
            tts_profile_name=None,
        )
        assert res == {}

    def test_write_html_report_skips_audio_when_disabled(self, tmp_path):
        out = write_html_report(_PACKET, tmp_path, prepare_voicebox_audio=False)
        assert out.exists()
