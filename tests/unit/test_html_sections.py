"""Tests for technologies.report_render.html.raw_html._sections."""

from __future__ import annotations

from social_research_probe.technologies.report_render.html.raw_html import _sections as sec


def _basic(**overrides):
    base = {
        "topic": "ai",
        "platform": "youtube",
        "purpose_set": ["career"],
        "items_top_n": [],
        "source_validation_summary": {},
        "platform_engagement_summary": "",
        "evidence_summary": "",
        "stats_summary": {"highlights": [], "low_confidence": False},
        "chart_captions": [],
        "warnings": [],
    }
    base.update(overrides)
    return base


def test_section1():
    assert "Topic" in sec.section_1_topic_purpose(_basic())


def test_section2():
    assert "youtube" in sec.section_2_platform(_basic())


def test_section3_no_items():
    assert "no items" in sec.section_3_top_items(_basic())


def test_section3_with_items():
    items = [
        {
            "channel": "Ch",
            "url": "https://x",
            "title": "T1",
            "source_class": "primary",
            "scores": {"trust": 0.9, "trend": 0.8, "opportunity": 0.7, "overall": 0.85},
            "one_line_takeaway": "tk",
            "transcript": "x" * 4000,
            "summary_source": "description",
        }
    ]
    out = sec.section_3_top_items(_basic(items_top_n=items))
    assert "Ch" in out and "Transcript" in out and "summary-notice" in out


def test_section4():
    out = sec.section_4_platform_engagement(_basic(platform_engagement_summary="a; b"))
    assert "<li>" in out


def test_section4_empty():
    out = sec.section_4_platform_engagement(_basic())
    assert "no data" in out


def test_section5_with_notes():
    svs = {
        "validated": 5,
        "partially": 1,
        "unverified": 0,
        "low_trust": 0,
        "primary": 5,
        "secondary": 0,
        "commentary": 0,
        "notes": "ok",
    }
    out = sec.section_5_source_validation(_basic(source_validation_summary=svs))
    assert "Notes" in out


def test_section5_no_notes():
    svs = {"validated": 1}
    out = sec.section_5_source_validation(_basic(source_validation_summary=svs))
    assert "Notes" not in out


def test_section6():
    assert "<li>" in sec.section_6_evidence(_basic(evidence_summary="x; y"))


def test_section7_empty():
    assert "no highlights" in sec.section_7_statistics(_basic())


def test_section7_with_highlights_and_low_conf():
    out = sec.section_7_statistics(
        _basic(
            stats_summary={
                "highlights": ["Mean overall: 0.5 — value", "Pearson r between a and b: 0.5"],
                "low_confidence": True,
            }
        )
    )
    assert "Low confidence" in out


def test_split_metric_finding_dash():
    a, b = sec._split_metric_finding("foo — bar")
    assert a == "foo" and b == "bar"


def test_split_metric_finding_colon():
    a, b = sec._split_metric_finding("foo: bar")
    assert a == "foo" and b == "bar"


def test_split_metric_finding_neither():
    a, b = sec._split_metric_finding("plain")
    assert a == "plain" and b == ""


def test_what_it_means():
    out = sec._what_it_means("Mean overall: 0.5", "0.5", "descriptive", "ai", ["latest-news"])
    assert isinstance(out, str)


def test_section8_no_charts():
    assert "no charts rendered" in sec.section_8_charts(_basic(), None)


def test_section8_with_caption(tmp_path):
    out = sec.section_8_charts(_basic(chart_captions=["Bar chart: x (5 items)"]), tmp_path)
    assert "chart-block" in out


def test_chart_block_with_real_png(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    cap = f"Bar chart: x (1 items)\n_(see PNG: {png})_"
    out = sec._chart_block(cap, tmp_path)
    assert 'src="data:image/png' in out


def test_chart_block_unknown_path(tmp_path):
    out = sec._chart_block("Random caption", tmp_path)
    assert "chart-block" in out


def test_chart_block_with_ascii(tmp_path):
    cap = "Title line\nascii art content"
    out = sec._chart_block(cap, tmp_path)
    assert "chart-ascii" in out


def test_find_chart_path_none():
    assert sec._find_chart_path("anything", None) is None


def test_find_chart_path_pngref(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"x")
    cap = f"caption (see PNG: {png})"
    assert sec._find_chart_path(cap, tmp_path) == str(png)


def test_find_chart_path_pngref_missing(tmp_path):
    cap = f"caption (see PNG: {tmp_path}/nope.png)"
    assert sec._find_chart_path(cap, tmp_path) is None


def test_find_chart_path_bar_match(tmp_path):
    png = tmp_path / "x_bar.png"
    png.write_bytes(b"x")
    cap = "Bar chart: x (3 items)"
    assert sec._find_chart_path(cap, tmp_path) == str(png)


def test_find_chart_path_no_match(tmp_path):
    assert sec._find_chart_path("Random text", tmp_path) is None


def test_section9_empty():
    assert "(none)" in sec.section_9_warnings(_basic())


def test_section9_with():
    out = sec.section_9_warnings(_basic(warnings=["w1", "w2"]))
    assert "<ul" in out and "w1" in out


def test_section10_empty():
    assert "unavailable" in sec.section_10_synthesis(None)


def test_section10_with():
    assert "<p>" in sec.section_10_synthesis("Hello")


def test_section11():
    assert "unavailable" in sec.section_11_opportunity(None)
    assert "<p>" in sec.section_11_opportunity("Hello")


def test_section12():
    assert "unavailable" in sec.section_12_summary(None)
    assert "<p>" in sec.section_12_summary("Hello")
