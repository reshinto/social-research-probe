"""HTML section builders for the research report.

Each public function takes report data and returns an HTML string fragment
for one numbered section. Mirrors the section structure in
services/synthesizing/formatter.py but produces HTML instead of Markdown.
"""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path

from social_research_probe.services.synthesizing.explanations.topic_hint import (
    topic_action_hint,
)
from social_research_probe.services.synthesizing.formatter import (
    _contextual_explanation,
    _infer_model,
)
from social_research_probe.utils.core.types import ResearchReport, ScoredItem


def _esc(text: str) -> str:
    """HTML-escape a string for safe insertion into element content."""
    return html.escape(str(text), quote=False)


def section_1_topic_purpose(report: ResearchReport) -> str:
    """Section 1: Topic and purpose set."""
    purposes = _esc(", ".join(report["purpose_set"]))
    return (
        "<ul>"
        f"<li><strong>Topic:</strong> {_esc(report['topic'])}</li>"
        f"<li><strong>Purposes:</strong> {purposes}</li>"
        "</ul>"
    )


def section_2_platform(report: ResearchReport) -> str:
    """Section 2: Platform."""
    return f"<ul><li><strong>Platform:</strong> {_esc(report['platform'])}</li></ul>"


def section_3_top_items(report: ResearchReport) -> str:
    """Section 3: Scored top-N items with table and per-item links."""
    items = report.get("items_top_n", [])
    if not items:
        return "<p><em>(no items returned)</em></p>"
    return _items_score_table(items) + "\n" + _items_links(items)


def _items_score_table(items: list[ScoredItem]) -> str:
    """Render the score table for top items."""
    rows = [
        "<tr><th>#</th><th>Channel</th><th>Class</th><th>Trust</th>"
        "<th>Trend</th><th>Opp</th><th>Overall</th><th>Title</th></tr>"
    ]
    for i, it in enumerate(items, 1):
        sc = it.get("scores", {})
        rows.append(
            f"<tr><td>{i}</td><td>{_esc(it.get('channel', ''))}</td>"
            f"<td>{_esc(it.get('source_class', '?'))}</td>"
            f"<td>{sc.get('trust', 0):.2f}</td><td>{sc.get('trend', 0):.2f}</td>"
            f"<td>{sc.get('opportunity', 0):.2f}</td><td>{sc.get('overall', 0):.2f}</td>"
            f"<td>{_esc(it.get('title', ''))}</td></tr>"
        )
    return f'<div class="table-wrap"><table>{"".join(rows)}</table></div>'


def _items_links(items: list[ScoredItem]) -> str:
    """Render per-item URL + one-line takeaway as a bullet list."""
    lis = []
    for i, it in enumerate(items, 1):
        url = _esc(it.get("url", "#"))
        channel = _esc(it.get("channel", ""))
        takeaway = _esc(it.get("one_line_takeaway", ""))
        transcript = it.get("transcript", "")
        if transcript:
            extra = (
                "<details><summary>Transcript</summary>"
                f"<pre>{_esc(transcript[:3000])}{'...' if len(transcript) > 3000 else ''}</pre>"
                "</details>"
            )
        else:
            extra = ""
        description_notice = (
            '<p class="summary-notice"><em>Summary generated from the video\'s'
            " description — transcript unavailable.</em></p>"
            if it.get("summary_source") == "description"
            else ""
        )
        lis.append(
            f"<li><strong>[{i}]</strong> "
            f'<a href="{url}" rel="noopener noreferrer">{channel}</a>'
            f" — {takeaway}{description_notice}{extra}</li>"
        )
    return f"<ul>{''.join(lis)}</ul>"


def section_4_platform_engagement(report: ResearchReport) -> str:
    """Section 4: Platform signals as bullet list."""
    return _bulletise(report.get("platform_engagement_summary", ""))


def section_5_source_validation(report: ResearchReport) -> str:
    """Section 5: Source validation counts."""
    svs = report.get("source_validation_summary") or {}
    lines = [
        f"<li>Validated: {svs.get('validated', 0)}, Partial: {svs.get('partially', 0)}, "
        f"Unverified: {svs.get('unverified', 0)}, Low-trust: {svs.get('low_trust', 0)}</li>",
        f"<li>Primary / Secondary / Commentary: "
        f"{svs.get('primary', 0)} / {svs.get('secondary', 0)} / {svs.get('commentary', 0)}</li>",
    ]
    if svs.get("notes"):
        lines.append(f"<li>Notes: {_esc(svs['notes'])}</li>")
    return f"<ul>{''.join(lines)}</ul>"


def section_6_evidence(report: ResearchReport) -> str:
    """Section 6: Evidence summary as bullet list."""
    return _bulletise(report.get("evidence_summary", ""))


def section_7_statistics(report: ResearchReport) -> str:
    """Section 7: Statistics highlights table."""
    stats = report.get("stats_summary", {})
    highlights = stats.get("highlights", [])
    low_confidence = stats.get("low_confidence", False)
    topic = str(report.get("topic", ""))
    purposes = list(report.get("purpose_set", []) or [])
    result = (
        "<p><em>(no highlights)</em></p>"
        if not highlights
        else _highlights_table(highlights, topic, purposes)
    )
    if low_confidence:
        result += '<p><em style="color:#c0392b">Low confidence — interpret with caution.</em></p>'
    return result


def _split_metric_finding(line: str) -> tuple[str, str]:
    if " — " in line:
        a, b = line.split(" — ", 1)
        return a, b
    if ": " in line:
        a, _, b = line.partition(": ")
        return a, b
    return line, ""


def _what_it_means(metric: str, finding: str, model: str, topic: str, purposes: list[str]) -> str:
    """Combine the model's plain-English explanation with topic+purpose guidance."""
    base = _contextual_explanation(metric, finding)
    hint = topic_action_hint(model, topic, purposes)
    if base and hint:
        return f"{base} {hint}"
    return base or hint


def _highlights_table(highlights: list[str], topic: str, purposes: list[str]) -> str:
    """Render statistics highlights as a four-column HTML table."""
    rows = ["<tr><th>Model</th><th>Metric</th><th>Finding</th><th>What it means</th></tr>"]
    prev_model = None
    for h in highlights:
        metric, finding = _split_metric_finding(h)
        model = _infer_model(h) or _infer_model(metric)
        explanation = _what_it_means(h, finding, model, topic, purposes)
        model_cell = model if model != prev_model else ""
        prev_model = model
        rows.append(
            "<tr>"
            f"<td>{_esc(model_cell)}</td>"
            f"<td>{_esc(metric)}</td>"
            f"<td>{_esc(finding)}</td>"
            f"<td>{_esc(explanation)}</td>"
            "</tr>"
        )
    return f'<div class="table-wrap"><table>{"".join(rows)}</table></div>'


def section_8_charts(report: ResearchReport, charts_dir: Path | None) -> str:
    """Section 8: Embedded chart images and captions."""
    captions = report.get("chart_captions", [])
    if not captions:
        return "<p><em>(no charts rendered)</em></p>"
    blocks = []
    for cap in captions:
        blocks.append(_chart_block(cap, charts_dir))
    return "\n".join(blocks)


def _chart_block(caption: str, charts_dir: Path | None) -> str:
    """Render one chart: embedded image (if available) plus caption text."""
    png_path = _find_chart_path(caption, charts_dir)
    img_tag = ""
    if png_path:
        try:
            b64 = base64.b64encode(Path(png_path).read_bytes()).decode()
            img_tag = f'<img src="data:image/png;base64,{b64}" alt="" loading="lazy">'
        except OSError:
            pass

    # Strip the _(see PNG: ...)_ annotation from caption before display
    display_cap = re.sub(r"_\(see PNG:[^)]+\)_", "", caption).strip()
    # Split on first newline: first line is title, rest may be ASCII art
    parts = display_cap.split("\n", 1)
    title_html = _esc(parts[0])
    ascii_html = (
        f'<pre class="chart-ascii" aria-hidden="true">{_esc(parts[1])}</pre>'
        if len(parts) > 1 and parts[1].strip()
        else ""
    )
    return (
        '<div class="chart-block">'
        + img_tag
        + f'<p class="chart-caption">{title_html}</p>'
        + ascii_html
        + "</div>"
    )


def _find_chart_path(caption: str, charts_dir: Path | None) -> str | None:
    """Extract the PNG file path referenced in a chart caption, if available."""
    if charts_dir is None:
        return None
    # Most chart types embed path as _(see PNG: /absolute/path.png)_
    m = re.search(r"\(see PNG:\s*([^\)]+)\)", caption)
    if m:
        p = Path(m.group(1).strip())
        return str(p) if p.exists() else None
    # Bar chart embeds "Bar chart: <label> (N items)" — path is derivable
    m = re.match(r"Bar chart:\s+(\S+)\s*\(", caption)
    if m:
        slug = m.group(1).replace(" ", "_")
        p = charts_dir / f"{slug}_bar.png"
        return str(p) if p.exists() else None
    return None


def section_9_warnings(report: ResearchReport) -> str:
    """Section 9: Research warnings."""
    warnings = report.get("warnings", [])
    if not warnings:
        return "<p><em>(none)</em></p>"
    lis = "".join(f"<li>{_esc(w)}</li>" for w in warnings)
    return f'<ul class="warning-list">{lis}</ul>'


def section_10_synthesis(text: str | None) -> str:
    """Compiled Synthesis section (LLM-generated or placeholder)."""
    if not text:
        return "<p><em>(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)</em></p>"
    from social_research_probe.technologies.report_render.html.raw_html.markdown_to_html import (
        md_to_html,
    )

    return md_to_html(text)


def section_11_opportunity(text: str | None) -> str:
    """Opportunity Analysis section (LLM-generated or placeholder)."""
    if not text:
        return "<p><em>(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)</em></p>"
    from social_research_probe.technologies.report_render.html.raw_html.markdown_to_html import (
        md_to_html,
    )

    return md_to_html(text)


def section_12_summary(text: str | None) -> str:
    """Final Summary section (LLM-generated or placeholder)."""
    if not text:
        return "<p><em>(LLM summary unavailable — runner disabled or all runners failed; see terminal logs)</em></p>"
    from social_research_probe.technologies.report_render.html.raw_html.markdown_to_html import (
        md_to_html,
    )

    return md_to_html(text)


def _bulletise(text: str) -> str:
    """Convert a semicolon-separated summary string to an HTML bullet list."""
    parts = [p.strip() for p in text.split(";") if p.strip()]
    if not parts:
        return "<p><em>(no data)</em></p>"
    lis = "".join(f"<li>{_esc(p)}</li>" for p in parts)
    return f"<ul>{lis}</ul>"
