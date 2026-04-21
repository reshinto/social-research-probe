"""Packet formatting and Markdown rendering for srp research output.

Transforms a raw research packet (produced by the pipeline) into human-readable
Markdown sections 1-11. Also builds the canonical research packet dict.

Sections 1-9 are derived deterministically from packet data.
Sections 10-11 (Compiled Synthesis, Opportunity Analysis) are read from the
packet when available; otherwise a placeholder is shown.
"""

from __future__ import annotations

from social_research_probe.types import (
    ResearchPacket,
    ScoredItem,
    SourceValidationSummary,
    StatsSummary,
)

from .explanations import contextual_explanation as _contextual_explanation
from .explanations import infer_model as _infer_model

__all__ = ["build_packet", "render_full", "render_sections_1_9"]


def build_packet(
    *,
    topic: str,
    platform: str,
    purpose_set: list[str],
    items_top_n: list[ScoredItem],
    source_validation_summary: SourceValidationSummary,
    platform_signals_summary: str,
    evidence_summary: str,
    stats_summary: StatsSummary,
    chart_captions: list[str],
    warnings: list[str],
    chart_takeaways: list[str] | None = None,
) -> ResearchPacket:
    """Assemble the canonical packet dict passed between pipeline and renderer."""
    return {
        "topic": topic,
        "platform": platform,
        "purpose_set": purpose_set,
        "items_top_n": items_top_n,
        "source_validation_summary": source_validation_summary,
        "platform_signals_summary": platform_signals_summary,
        "evidence_summary": evidence_summary,
        "stats_summary": stats_summary,
        "chart_captions": chart_captions,
        "chart_takeaways": list(chart_takeaways or []),
        "warnings": warnings,
    }


def _items_table(items: list[ScoredItem]) -> str:
    """Render the top items as a markdown table for compact scanning."""
    header = (
        "| # | Channel | Class | Trust | Trend | Opp | Overall | Title |\n"
        "|---|---------|-------|-------|-------|-----|---------|-------|"
    )
    rows = []
    for i, it in enumerate(items, start=1):
        scores = it.get("scores", {})
        title = it["title"].replace("|", r"\|")
        rows.append(
            f"| {i} | {it['channel']} | {it.get('source_class', '?')} "
            f"| {scores.get('trust', 0):.2f} | {scores.get('trend', 0):.2f} "
            f"| {scores.get('opportunity', 0):.2f} | {scores.get('overall', 0):.2f} "
            f"| {title} |"
        )
    return "\n".join([header, *rows])


def _items_links_and_takeaways(items: list[ScoredItem]) -> str:
    """Render per-item URL and takeaway as a bullet list below the score table."""
    bullets = []
    for i, it in enumerate(items, start=1):
        bullets.append(
            f"- **[{i}]** [{it['channel']}]({it['url']}) — {it.get('one_line_takeaway', '')}"
        )
    return "\n".join(bullets)


def _highlights_table(highlights: list[str]) -> str:
    """Render stat highlights as a four-column markdown table.

    Columns: Model | Metric | Finding | What it means
    The Model column is left blank for consecutive rows of the same model to
    visually group related metrics. The 'What it means' column is generated
    dynamically from the actual metric value, not a static definition.
    """
    if not highlights:
        return "_(no highlights)_"
    header = (
        "| Model | Metric | Finding | What it means |\n|-------|--------|---------|---------------|"
    )
    rows = []
    prev_model = None
    for h in highlights:
        if " — " in h:
            metric, finding = h.split(" — ", 1)
        else:
            metric, finding = h, ""
        model = _infer_model(metric)
        explanation = _contextual_explanation(metric, finding)
        model_cell = model if model != prev_model else ""
        prev_model = model
        metric = metric.replace("|", r"\|")
        finding = finding.replace("|", r"\|")
        explanation = explanation.replace("|", r"\|")
        rows.append(f"| {model_cell} | {metric} | {finding} | {explanation} |")
    return "\n".join([header, *rows])


def _to_bullets(text: str) -> str:
    """Split a semicolon-separated summary string into a markdown bullet list."""
    return "\n".join(f"- {part.strip()}" for part in text.split(";") if part.strip())


_bulletise = _to_bullets


def render_full(
    packet: ResearchPacket,
) -> str:
    """Render all 11 sections as Markdown.

    Sections 1-9 are derived from the packet. Sections 10-11 are read from
    the packet itself; if omitted they indicate that synthesis was not stored.
    """
    body = render_sections_1_9(packet)
    s10 = (
        packet.get("compiled_synthesis")
        or "_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    s11 = (
        packet.get("opportunity_analysis")
        or "_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    body += f"\n## 10. Compiled Synthesis\n\n{s10}\n"
    body += f"\n## 11. Opportunity Analysis\n\n{s11}\n"
    footer = _render_timing_footer(packet.get("stage_timings", []))
    if footer:
        body += f"\n{footer}\n"
    return body


def _render_timing_footer(timings: list) -> str:
    """Return a one-line italic timing summary, or empty when no stages recorded."""
    if not timings:
        return ""
    parts = []
    total = 0.0
    for entry in timings:
        if not isinstance(entry, dict):
            continue
        name = entry.get("stage", "?")
        elapsed = float(entry.get("elapsed_s", 0.0))
        total += elapsed
        parts.append(f"{name} {elapsed:.1f}s")
    if not parts:
        return ""
    return "_Timing: " + " • ".join(parts) + f" • total {total:.1f}s_"


def render_sections_1_9(packet: ResearchPacket) -> str:
    """Render sections 1-9 deterministically from packet data.

    Each section maps directly to a field in the packet. This function is
    also called by render_full and by tests that verify section formatting
    without requiring LLM synthesis.
    """
    svs = packet["source_validation_summary"]
    items = packet["items_top_n"]
    stats = packet["stats_summary"]
    warnings = packet.get("warnings", [])
    parts: list[str] = []
    parts.append(
        "## 1. Topic & Purpose\n\n"
        f"- **Topic:** {packet['topic']}\n"
        f"- **Purposes:** {', '.join(packet['purpose_set'])}"
    )
    parts.append(f"## 2. Platform\n\n- **Platform:** {packet['platform']}")
    if items:
        parts.append(
            "## 3. Top Items\n\n"
            + _items_table(items)
            + "\n\n**Links & takeaways:**\n\n"
            + _items_links_and_takeaways(items)
        )
    else:
        parts.append("## 3. Top Items\n\n_(no items returned)_")
    parts.append("## 4. Platform Signals\n\n" + _to_bullets(packet["platform_signals_summary"]))
    parts.append(
        "## 5. Source Validation\n\n"
        f"- validated: {svs['validated']}, partial: {svs['partially']}, "
        f"unverified: {svs['unverified']}, low-trust: {svs['low_trust']}\n"
        f"- primary/secondary/commentary: {svs['primary']}/{svs['secondary']}/{svs['commentary']}"
        + (f"\n- notes: {svs['notes']}" if svs.get("notes") else "")
    )
    parts.append("## 6. Evidence\n\n" + _to_bullets(packet["evidence_summary"]))
    lc = "\n\n_low confidence — interpret with caution_" if stats.get("low_confidence") else ""
    highlights = stats.get("highlights", [])
    parts.append(f"## 7. Statistics\n\n{_highlights_table(highlights)}{lc}")
    caps = packet.get("chart_captions", [])
    parts.append("## 8. Charts\n\n" + ("\n\n".join(caps) if caps else "_(no charts rendered)_"))
    parts.append(
        "## 9. Warnings\n\n" + ("\n".join(f"- {w}" for w in warnings) if warnings else "_(none)_")
    )
    return "\n\n".join(parts) + "\n"
