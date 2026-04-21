"""Evidence tests — HTML report renderer produces well-formed, content-bearing HTML.

Two services: ``render_html`` (in-memory assembly) and ``write_html_report``
(file output). We assert:

- The rendered document contains the packet's topic verbatim in the body.
- The document parses as well-formed HTML via ``html.parser``.
- ``write_html_report`` places a file under ``<data_dir>/reports/`` and the
  file is a valid UTF-8 document containing the topic.

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| render_html | packet with topic='AI agents' | contains '&lt;h1' and topic text | _build_body |
| render_html | packet with platform='youtube' | renders without error | optional field path |
| write_html_report | packet + tmp data_dir | file in reports/ dir, size > 1kb, utf-8 | file I/O path |
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

from social_research_probe.render.html import render_html, write_html_report


class _WellFormedChecker(HTMLParser):
    """Parses HTML and records any parser errors (none expected)."""

    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def error(self, message):  # type: ignore[override]
        self.errors.append(message)


def _minimal_packet(topic: str = "AI agents") -> dict:
    """Build the minimum packet the render pipeline accepts.

    The section builders access ``topic``, ``platform``, ``purpose_set``, and
    ``source_validation_summary`` without ``.get()`` fallback, so those must
    be present even when empty.
    """
    return {
        "topic": topic,
        "platform": "youtube",
        "purpose_set": [],
        "source_validation_summary": {
            "validated": 0,
            "partially": 0,
            "unverified": 0,
            "low_trust": 0,
            "primary": 0,
            "secondary": 0,
            "commentary": 0,
        },
        "items_top5": [],
        "signal_summary": "",
        "evidence_summary": "",
    }


def test_render_html_contains_topic_verbatim():
    html_doc = render_html(_minimal_packet("Test Research Topic"))
    assert "Test Research Topic" in html_doc


def test_render_html_is_well_formed():
    html_doc = render_html(_minimal_packet())
    parser = _WellFormedChecker()
    parser.feed(html_doc)
    parser.close()
    assert parser.errors == []
    # At minimum, the report should have <html>, <body>, <h1>, and <main>.
    for tag in ("<html", "<body", "<h1", "<main"):
        assert tag in html_doc


def test_render_html_handles_packet_with_required_fields_only():
    """Sections need topic/platform/purpose_set/source_validation_summary."""
    html_doc = render_html(_minimal_packet("Minimal"))
    assert "Minimal" in html_doc


def test_write_html_report_writes_utf8_file_under_reports_dir(tmp_path):
    packet = _minimal_packet("File Output Topic")
    out_path = write_html_report(packet, data_dir=tmp_path)
    assert out_path.parent == tmp_path / "reports"
    assert out_path.exists()
    assert out_path.suffix == ".html"
    content = out_path.read_text(encoding="utf-8")
    assert "File Output Topic" in content
    assert out_path.stat().st_size > 1000  # non-trivial size
