from __future__ import annotations

from typing import Any

RESPONSE_SCHEMA = {
    "compiled_synthesis": "string ≤150 words",
    "opportunity_analysis": "string ≤150 words",
}


def build_packet(
    *,
    topic: str,
    platform: str,
    purpose_set: list[str],
    items_top5: list[dict],
    source_validation_summary: dict,
    platform_signals_summary: str,
    evidence_summary: str,
    stats_summary: dict,
    chart_captions: list[str],
    warnings: list[str],
) -> dict:
    return {
        "topic": topic,
        "platform": platform,
        "purpose_set": purpose_set,
        "items_top5": items_top5,
        "source_validation_summary": source_validation_summary,
        "platform_signals_summary": platform_signals_summary,
        "evidence_summary": evidence_summary,
        "stats_summary": stats_summary,
        "chart_captions": chart_captions,
        "warnings": warnings,
        "response_schema": RESPONSE_SCHEMA,
    }


def _items_table(items: list[dict]) -> str:
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


def _items_links_and_takeaways(items: list[dict]) -> str:
    """Render per-item URL and takeaway as a separate bullet list."""
    bullets = []
    for i, it in enumerate(items, start=1):
        bullets.append(
            f"- **[{i}]** [{it['channel']}]({it['url']}) — {it.get('one_line_takeaway', '')}"
        )
    return "\n".join(bullets)


def _highlights_table(highlights: list[str]) -> str:
    """Render stat highlights as a two-column markdown table: Metric | Finding."""
    if not highlights:
        return "_(no highlights)_"
    header = "| Metric | Finding |\n|--------|---------|"
    rows = []
    for h in highlights:
        if " — " in h:
            metric, finding = h.split(" — ", 1)
        else:
            metric, finding = h, ""
        metric = metric.replace("|", r"\|")
        finding = finding.replace("|", r"\|")
        rows.append(f"| {metric} | {finding} |")
    return "\n".join([header, *rows])


def _bulletise(text: str) -> str:
    """Split a semicolon-separated summary into a bullet list."""
    return "\n".join(f"- {part.strip()}" for part in text.split(";") if part.strip())


def render_full(
    packet: dict[str, Any],
    compiled_synthesis: str | None = None,
    opportunity_analysis: str | None = None,
) -> str:
    """Render all 11 sections as Markdown.

    Sections 1–9 are derived from the packet. Sections 10–11 use the
    provided synthesis strings; if omitted they indicate that LLM synthesis
    was not run (e.g. plain CLI mode without a configured runner).
    """
    body = render_sections_1_9(packet)
    s10 = compiled_synthesis or "_(LLM synthesis not run — use skill mode for AI analysis)_"
    s11 = opportunity_analysis or "_(LLM synthesis not run — use skill mode for AI analysis)_"
    body += f"\n## 10. Compiled Synthesis\n\n{s10}\n"
    body += f"\n## 11. Opportunity Analysis\n\n{s11}\n"
    return body


def render_sections_1_9(packet: dict[str, Any]) -> str:
    svs = packet["source_validation_summary"]
    items = packet["items_top5"]
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
    parts.append("## 4. Platform Signals\n\n" + _bulletise(packet["platform_signals_summary"]))
    parts.append(
        "## 5. Source Validation\n\n"
        f"- validated: {svs['validated']}, partial: {svs['partially']}, "
        f"unverified: {svs['unverified']}, low-trust: {svs['low_trust']}\n"
        f"- primary/secondary/commentary: {svs['primary']}/{svs['secondary']}/{svs['commentary']}"
        + (f"\n- notes: {svs['notes']}" if svs.get("notes") else "")
    )
    parts.append("## 6. Evidence\n\n" + _bulletise(packet["evidence_summary"]))
    models = ", ".join(stats.get("models_run", [])) or "none"
    lc = " (low confidence)" if stats.get("low_confidence") else ""
    highlights = stats.get("highlights", [])
    parts.append(f"## 7. Statistics\n\n**Models:** {models}{lc}\n\n{_highlights_table(highlights)}")
    caps = packet.get("chart_captions", [])
    parts.append("## 8. Charts\n\n" + ("\n\n".join(caps) if caps else "_(no charts rendered)_"))
    parts.append(
        "## 9. Warnings\n\n" + ("\n".join(f"- {w}" for w in warnings) if warnings else "_(none)_")
    )
    return "\n\n".join(parts) + "\n"
