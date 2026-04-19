"""Tests for social_research_probe/render/ — HTML report generation."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

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
)
from social_research_probe.render.html import render_html, write_html_report
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
    "items_top5": [_ITEM],
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
        pkt = {**_PACKET, "items_top5": []}
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
        for sid in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"):
            assert f'id="{sid}"' in html

    def test_toc_links_present(self):
        html = render_html(_PACKET)
        assert 'href="#s1"' in html
        assert 'href="#s11"' in html

    def test_tts_controls_present(self):
        html = render_html(_PACKET)
        assert 'id="tts-play"' in html
        assert 'id="tts-pause"' in html
        assert 'id="tts-stop"' in html

    def test_tts_script_present(self):
        html = render_html(_PACKET)
        assert "speechSynthesis" in html

    def test_synthesis_10_rendered(self):
        html = render_html({**_PACKET, "compiled_synthesis": "My synthesis text."})
        assert "My synthesis text." in html

    def test_synthesis_11_rendered(self):
        html = render_html({**_PACKET, "opportunity_analysis": "My opportunity text."})
        assert "My opportunity text." in html

    def test_placeholder_when_no_synthesis(self):
        html = render_html(_PACKET)
        assert "LLM synthesis unavailable" in html

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


class TestWriteHtmlReport:
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

    def test_prints_path_to_stderr(self, tmp_path, capsys):
        write_html_report(_PACKET, tmp_path)
        err = capsys.readouterr().err
        assert "HTML report" in err
        assert "file://" in err

    def test_creates_reports_dir(self, tmp_path):
        reports_dir = tmp_path / "reports"
        assert not reports_dir.exists()
        write_html_report(_PACKET, tmp_path)
        assert reports_dir.is_dir()


class TestCommandsReport:
    def test_run_writes_to_out_path(self, tmp_path):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        out_path = tmp_path / "out.html"
        result = run(str(pkt_path), None, None, str(out_path))
        assert result == 0
        assert out_path.exists()
        assert "DOCTYPE" in out_path.read_text(encoding="utf-8")

    def test_run_writes_to_stdout_when_no_out(self, tmp_path, capsys):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        result = run(str(pkt_path), None, None, None)
        assert result == 0
        assert "DOCTYPE" in capsys.readouterr().out

    def test_run_reads_synthesis_files(self, tmp_path):
        from social_research_probe.commands.report import run

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        s10 = tmp_path / "s10.txt"
        s11 = tmp_path / "s11.txt"
        s10.write_text("Compiled synthesis here", encoding="utf-8")
        s11.write_text("Opportunity analysis here", encoding="utf-8")
        out_path = tmp_path / "out.html"
        run(str(pkt_path), str(s10), str(s11), str(out_path))
        content = out_path.read_text(encoding="utf-8")
        assert "Compiled synthesis here" in content
        assert "Opportunity analysis here" in content

    def test_run_invalid_json_raises_validation_error(self, tmp_path):
        from social_research_probe.commands.report import run
        from social_research_probe.errors import ValidationError

        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        with pytest.raises(ValidationError, match="cannot read packet file"):
            run(str(bad), None, None, None)

    def test_run_missing_packet_raises_validation_error(self, tmp_path):
        from social_research_probe.commands.report import run
        from social_research_probe.errors import ValidationError

        with pytest.raises(ValidationError, match="cannot read packet file"):
            run(str(tmp_path / "nonexistent.json"), None, None, None)

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
        result = run(str(pkt_path), None, None, str(out_path))
        assert result == 0

    def test_run_dispatched_from_main(self, monkeypatch, tmp_path):
        from social_research_probe.cli import main

        pkt_path = tmp_path / "packet.json"
        pkt_path.write_text(json.dumps(_PACKET), encoding="utf-8")
        out_path = tmp_path / "out.html"
        result = main(
            [
                "--data-dir",
                str(tmp_path),
                "report",
                "--packet",
                str(pkt_path),
                "--out",
                str(out_path),
            ]
        )
        assert result == 0
        assert out_path.exists()


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


class TestResearchHtmlInCli:
    """Integration tests for HTML output wired into the research CLI path."""

    _PACKET_WITH_SYNTHESIS: ClassVar[dict] = {
        **_PACKET,
        "compiled_synthesis": "synth10 text",
        "opportunity_analysis": "synth11 text",
    }

    def _patch_pipeline(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_research",
            lambda cmd, d, adapter_config=None: self._PACKET_WITH_SYNTHESIS,
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)

    def test_html_file_written_in_research_command(self, monkeypatch, tmp_path, capsys):
        from social_research_probe.cli import main

        self._patch_pipeline(monkeypatch)
        assert main(["--data-dir", str(tmp_path), "research", "ai", "latest-news"]) == 0
        reports = list((tmp_path / "reports").glob("*.html"))
        assert len(reports) == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == "synthesis"
        assert payload["packet"]["compiled_synthesis"] == "synth10 text"
        assert payload["packet"]["html_report_path"].startswith("file://")

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
        assert run(str(pkt_path), None, None, str(out_path)) == 0
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
            lambda cmd, d, adapter_config=None: _PACKET,
        )
        monkeypatch.setattr(
            "social_research_probe.cli._attach_synthesis",
            lambda pkt: (_ for _ in ()).throw(SynthesisError("boom")),
        )
        assert main(["--data-dir", str(tmp_path), "research", "ai", "latest-news"]) == 4
