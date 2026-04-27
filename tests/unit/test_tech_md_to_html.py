"""Tests for tech.report_render.html.raw_html.markdown_to_html."""

from __future__ import annotations

from social_research_probe.technologies.report_render.html.raw_html.markdown_to_html import (
    md_to_html,
)


def test_heading():
    assert "<h2>Hi</h2>" in md_to_html("# Hi")


def test_heading_levels():
    out = md_to_html("## Sub")
    assert "<h3>Sub</h3>" in out


def test_bullet_list():
    out = md_to_html("- a\n- b")
    assert "<ul>" in out and "</ul>" in out
    assert "<li>a</li>" in out


def test_ordered_list():
    out = md_to_html("1. one\n2. two")
    assert "<ol>" in out and "<li>one</li>" in out


def test_horizontal_rule():
    assert "<hr>" in md_to_html("---")


def test_bold_italic():
    out = md_to_html("**bold** and *it*")
    assert "<strong>bold</strong>" in out
    assert "<em>it</em>" in out


def test_code():
    out = md_to_html("`code`")
    assert "<code>code</code>" in out


def test_link():
    out = md_to_html("[label](https://x)")
    assert '<a href="https://x"' in out
    assert ">label</a>" in out


def test_paragraph():
    out = md_to_html("Hello world")
    assert "<p>Hello world</p>" in out


def test_html_escaping():
    out = md_to_html("<script>")
    assert "&lt;script&gt;" in out


def test_blank_lines_collapsed():
    out = md_to_html("a\n\n\nb")
    assert out.count("\n\n\n") == 0


def test_list_switching_ol_to_ul():
    out = md_to_html("1. one\n- bullet")
    assert "<ol>" in out and "<ul>" in out
