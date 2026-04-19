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


def _fmt_item(i: int, it: dict) -> str:
    s = it.get("scores", {})
    return (
        f"{i}. **{it['title']}** — {it['channel']} — {it['url']}\n"
        f"   class={it.get('source_class', '?')} "
        f"trust={s.get('trust', 0):.2f} trend={s.get('trend', 0):.2f} "
        f"opportunity={s.get('opportunity', 0):.2f} overall={s.get('overall', 0):.2f}\n"
        f"   > {it.get('one_line_takeaway', '')}"
    )


def render_sections_1_9(packet: dict[str, Any]) -> str:
    svs = packet["source_validation_summary"]
    items = packet["items_top5"]
    stats = packet["stats_summary"]
    warnings = packet.get("warnings", [])
    parts: list[str] = []
    parts.append(
        f"## 1. Topic & Purpose\n\n{packet['topic']} — purposes: {', '.join(packet['purpose_set'])}"
    )
    parts.append(f"## 2. Platform\n\n{packet['platform']}")
    if items:
        parts.append(
            "## 3. Top Items\n\n" + "\n\n".join(_fmt_item(i + 1, it) for i, it in enumerate(items))
        )
    else:
        parts.append("## 3. Top Items\n\n_(no items returned)_")
    parts.append(f"## 4. Platform Signals\n\n{packet['platform_signals_summary']}")
    parts.append(
        "## 5. Source Validation\n\n"
        f"- validated: {svs['validated']}, partial: {svs['partially']}, "
        f"unverified: {svs['unverified']}, low-trust: {svs['low_trust']}\n"
        f"- primary/secondary/commentary: {svs['primary']}/{svs['secondary']}/{svs['commentary']}"
        + (f"\n- notes: {svs['notes']}" if svs.get("notes") else "")
    )
    parts.append(f"## 6. Evidence\n\n{packet['evidence_summary']}")
    models = ", ".join(stats.get("models_run", [])) or "none"
    lc = " (low confidence)" if stats.get("low_confidence") else ""
    highlights = "\n".join(f"- {h}" for h in stats.get("highlights", [])) or "_(no highlights)_"
    parts.append(f"## 7. Statistics\n\nModels: {models}{lc}\n\n{highlights}")
    caps = packet.get("chart_captions", [])
    parts.append(
        "## 8. Charts\n\n"
        + ("\n".join(f"- {c}" for c in caps) if caps else "_(no charts rendered)_")
    )
    parts.append(
        "## 9. Warnings\n\n" + ("\n".join(f"- {w}" for w in warnings) if warnings else "_(none)_")
    )
    return "\n\n".join(parts) + "\n"
