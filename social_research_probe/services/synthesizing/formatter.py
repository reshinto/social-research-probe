"""Packet formatting and Markdown rendering for srp research output.

Transforms a raw research packet (produced by the pipeline) into a
human-readable Markdown report. Also builds the canonical research packet dict.

The deterministic report body comes from packet data. Compiled Synthesis,
Opportunity Analysis, and Final Summary come from the packet when available;
Final Summary falls back to a deterministic summary built from existing packet
data when synthesis is disabled.
"""

from __future__ import annotations

import re
from functools import lru_cache

from social_research_probe.utils.core.types import (
    ResearchPacket,
    ScoredItem,
    SourceValidationSummary,
    StatsSummary,
)

from .explanations import contextual_explanation as _contextual_explanation
from .explanations import infer_model as _infer_model

__all__ = [
    "build_fallback_report_summary",
    "build_packet",
    "render_full",
    "render_sections_1_9",
    "resolve_report_summary",
]

_UNAVAILABLE_SUMMARY_MARKERS = (
    "LLM synthesis unavailable",
    "LLM summary unavailable",
)


def build_packet(
    *,
    topic: str,
    platform: str,
    purpose_set: list[str],
    items_top_n: list[ScoredItem],
    source_validation_summary: SourceValidationSummary,
    platform_engagement_summary: str,
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
        "platform_engagement_summary": platform_engagement_summary,
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
    """Render the full Markdown report from packet data and synthesis text."""
    body = render_sections_1_9(packet)
    compiled_synthesis_text = (
        packet.get("compiled_synthesis")
        or "_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    opportunity_analysis_text = (
        packet.get("opportunity_analysis")
        or "_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    final_summary_text = (
        resolve_report_summary(packet)
        or "_(LLM summary unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    body += f"\n## 10. Compiled Synthesis\n\n{compiled_synthesis_text}\n"
    body += f"\n## 11. Opportunity Analysis\n\n{opportunity_analysis_text}\n"
    body += f"\n## 12. Final Summary\n\n{final_summary_text}\n"
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
    parts.append("## 4. Platform Signals\n\n" + _to_bullets(packet["platform_engagement_summary"]))
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


def resolve_report_summary(packet: ResearchPacket) -> str | None:
    """Return the best available section-12 summary for *packet*."""
    report_summary = _usable_summary_text(packet.get("report_summary"))
    if report_summary:
        return report_summary
    return build_fallback_report_summary(packet)


def build_fallback_report_summary(packet: ResearchPacket) -> str | None:
    """Build a non-LLM final summary from existing packet data."""
    sentences: list[str] = []
    topic = str(packet.get("topic", "") or "").strip()
    platform = str(packet.get("platform", "") or "").strip()
    if topic and platform:
        sentences.append(f"This report covers {topic} on {platform}.")
    elif topic:
        sentences.append(f"This report covers {topic}.")

    source_validation = packet.get("source_validation_summary", {})
    if isinstance(source_validation, dict):
        validated = int(source_validation.get("validated", 0) or 0)
        partially = int(source_validation.get("partially", 0) or 0)
        unverified = int(source_validation.get("unverified", 0) or 0)
        low_trust = int(source_validation.get("low_trust", 0) or 0)
        if any((validated, partially, unverified, low_trust)):
            sentences.append(
                "Source validation: "
                f"{validated} validated, {partially} partial, "
                f"{unverified} unverified, and {low_trust} low-trust sources."
            )

    compiled = _plain_sentences(packet.get("compiled_synthesis"), limit=1)
    if compiled:
        sentences.append("Compiled synthesis: " + " ".join(compiled))

    opportunity = _plain_sentences(packet.get("opportunity_analysis"), limit=1)
    if opportunity:
        sentences.append("Opportunity analysis: " + " ".join(opportunity))

    stats_summary = packet.get("stats_summary", {})
    highlights = _plain_list_sentences(list(stats_summary.get("highlights", []) or []), limit=2)
    if highlights:
        sentences.append("Statistics highlights: " + " ".join(highlights))
    elif stats_summary.get("low_confidence"):
        sentences.append("Statistics are low confidence because the sample is small.")

    chart_takeaways = _plain_list_sentences(list(packet.get("chart_takeaways", []) or []), limit=2)
    if chart_takeaways:
        sentences.append("Chart signals: " + " ".join(chart_takeaways))

    signal_summary = _summary_sentences(packet.get("platform_engagement_summary", ""), limit=2)
    if signal_summary:
        sentences.append("Platform engagement: " + " ".join(signal_summary))

    evidence_summary = _summary_sentences(packet.get("evidence_summary", ""), limit=2)
    if evidence_summary:
        sentences.append("Evidence summary: " + " ".join(evidence_summary))

    warnings = _plain_list_sentences(list(packet.get("warnings", []) or []), limit=1)
    if warnings:
        sentences.append("Cautions: " + " ".join(warnings))

    if not sentences:
        return None
    return " ".join(sentences)


def _usable_summary_text(value: object) -> str:
    """Return a clean stored summary value, filtering known placeholders."""
    text = str(value or "").strip()
    if not text:
        return ""
    if any(marker in text for marker in _UNAVAILABLE_SUMMARY_MARKERS):
        return ""
    return text


@lru_cache(maxsize=128)
def _markdown_to_plain_text(text: str) -> str:
    """Collapse markdown-ish text into plain prose."""
    cleaned = text.replace("\r\n", "\n")
    cleaned = re.sub(r"```.+?```", " ", cleaned, flags=re.S)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned, flags=re.M)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.M)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.M)
    cleaned = re.sub(r"[*_~]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _plain_sentences(value: object, *, limit: int) -> list[str]:
    """Return up to *limit* cleaned sentences from markdown-ish text."""
    raw = _usable_summary_text(value)
    if not raw:
        return []
    cleaned = _markdown_to_plain_text(raw)
    if not cleaned:
        return []
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    if not parts:
        parts = [cleaned]
    return [_ensure_sentence(part) for part in parts[:limit]]


def _plain_list_sentences(values: list[object], *, limit: int) -> list[str]:
    """Return up to *limit* cleaned sentences from a list of text fragments."""
    sentences: list[str] = []
    for value in values:
        for sentence in _plain_sentences(value, limit=1):
            sentences.append(sentence)
            if len(sentences) >= limit:
                return sentences
    return sentences


def _summary_sentences(text: str | None, *, limit: int) -> list[str]:
    """Return up to *limit* sentences from a semicolon-separated packet summary."""
    raw = _usable_summary_text(text)
    if not raw:
        return []
    parts = [part.strip() for part in raw.split(";") if part.strip()]
    return [_ensure_sentence(_markdown_to_plain_text(part)) for part in parts[:limit]]


def _ensure_sentence(text: str) -> str:
    """Ensure summary text ends with sentence punctuation."""
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        return cleaned + "."
    return cleaned
