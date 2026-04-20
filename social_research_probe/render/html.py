"""HTML report renderer for srp research packets.

Produces a single self-contained HTML file with embedded chart images
(base64 PNG), a sticky TOC, and Web Speech API text-to-speech controls.
The output is identical regardless of whether research was triggered by
the skill or the CLI — both call write_html_report() after obtaining a
ResearchPacket.
"""

from __future__ import annotations

import html
import re
import sys
from datetime import datetime
from pathlib import Path

from social_research_probe.render._assets import CSS_STYLES, TTS_SCRIPT
from social_research_probe.render._sections import (
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
from social_research_probe.types import ResearchPacket

_SECTIONS = [
    ("s1", "1. Topic &amp; Purpose"),
    ("s2", "2. Platform"),
    ("s3", "3. Top Items"),
    ("s4", "4. Platform Signals"),
    ("s5", "5. Source Validation"),
    ("s6", "6. Evidence"),
    ("s7", "7. Statistics"),
    ("s8", "8. Charts"),
    ("s9", "9. Warnings"),
    ("s10", "10. Compiled Synthesis"),
    ("s11", "11. Opportunity Analysis"),
]


def render_html(
    packet: ResearchPacket,
    charts_dir: Path | None = None,
) -> str:
    """Render a complete self-contained HTML report for a research packet.

    Args:
        packet: The research packet produced by pipeline.run_research().
        charts_dir: Directory containing chart PNGs to embed. None → skip images.

    Returns:
        A complete HTML document as a string.
    """
    section_bodies = [
        section_1_topic_purpose(packet),
        section_2_platform(packet),
        section_3_top_items(packet),
        section_4_platform_signals(packet),
        section_5_source_validation(packet),
        section_6_evidence(packet),
        section_7_statistics(packet),
        section_8_charts(packet, charts_dir),
        section_9_warnings(packet),
        section_10_synthesis(packet.get("compiled_synthesis")),
        section_11_opportunity(packet.get("opportunity_analysis")),
    ]
    body_html = _build_body(packet, section_bodies)
    toc_html = _build_toc()
    return _page_shell(packet, toc_html, body_html)


def write_html_report(
    packet: ResearchPacket,
    data_dir: Path,
) -> Path:
    """Write an HTML report to data_dir/reports/ and return its path.

    Args:
        packet: Research packet from the pipeline.
        data_dir: Root data directory (charts live at data_dir/charts/).

    Returns:
        Absolute path to the written HTML file.
    """
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^\w-]", "-", packet["topic"].lower())[:40].strip("-")
    platform = packet.get("platform", "unknown")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = reports_dir / f"{slug}-{platform}-{ts}.html"

    html_content = render_html(packet, charts_dir=data_dir / "charts")
    out_path.write_text(html_content, encoding="utf-8")
    print(f"[srp] HTML report: {out_path.resolve().as_uri()}", file=sys.stderr)
    return out_path


def _build_toc() -> str:
    """Build the sidebar table-of-contents HTML."""
    links = "".join(f'<a href="#{sid}">{label}</a>' for sid, label in _SECTIONS)
    return f"<h2>Contents</h2>{links}"


def _build_body(packet: ResearchPacket, section_bodies: list[str]) -> str:
    """Build the <main> report body from section bodies."""
    topic_esc = html.escape(packet["topic"])
    platform_esc = html.escape(packet.get("platform", ""))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        f'<h1 class="report-title">{topic_esc}</h1>',
        f'<p class="report-meta">Platform: {platform_esc} &nbsp;·&nbsp; Generated: {timestamp}</p>',
    ]
    for (sid, label), body in zip(_SECTIONS, section_bodies, strict=True):
        parts.append(f'<section id="{sid}"><h2>{label}</h2>{body}</section>')
    return "\n".join(parts)


def _page_shell(packet: ResearchPacket, toc_html: str, body_html: str) -> str:
    """Assemble the complete HTML document from its parts."""
    title = html.escape(f"Research Report: {packet['topic']}")
    tts_bar = (
        '<div id="tts-bar">'
        '<button id="tts-play">\u25b6 Play</button>'
        '<button id="tts-pause" disabled>\u23f8 Pause</button>'
        '<button id="tts-stop" disabled>\u23f9 Stop</button>'
        '<label for="tts-rate" style="font-size:.8rem;opacity:.7">Speed</label>'
        '<select id="tts-rate">'
        '<option value="0.75">0.75\u00d7</option>'
        '<option value="1" selected>1\u00d7</option>'
        '<option value="1.25">1.25\u00d7</option>'
        '<option value="1.5">1.5\u00d7</option>'
        '<option value="2">2\u00d7</option>'
        "</select>"
        '<label for="tts-voice" style="font-size:.8rem;opacity:.7">Voice</label>'
        '<select id="tts-voice"></select>'
        '<span id="tts-label"></span>'
        "</div>"
    )
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{title}</title>\n"
        f"<style>{CSS_STYLES}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{tts_bar}\n"
        '<div id="layout">\n'
        f'<nav id="toc">{toc_html}</nav>\n'
        f'<main id="report-body">{body_html}</main>\n'
        "</div>\n"
        f"<script>{TTS_SCRIPT}</script>\n"
        "</body>\n"
        "</html>"
    )
