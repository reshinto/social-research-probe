"""Summary and follow-up generation for comparison results."""

from __future__ import annotations

from social_research_probe.utils.comparison.types import ComparisonResult

_MAX_FOLLOW_UPS = 5


def build_counts(result: ComparisonResult) -> dict[str, int]:
    """Count items by status across all change lists."""
    counts: dict[str, int] = {}

    for prefix, changes in [
        ("sources", result["source_changes"]),
        ("claims", result["claim_changes"]),
        ("narratives", result["narrative_changes"]),
    ]:
        for status in ("new", "repeated", "disappeared"):
            counts[f"{prefix}_{status}"] = sum(1 for c in changes if c["status"] == status)

    narr_changes = result["narrative_changes"]
    counts["narratives_strengthened"] = sum(
        1 for n in narr_changes if n.get("strength_signal") == "strengthened"
    )
    counts["narratives_weakened"] = sum(
        1 for n in narr_changes if n.get("strength_signal") == "weakened"
    )
    counts["trend_count"] = len(result["trends"])
    return counts


def format_console_summary(result: ComparisonResult) -> str:
    """Format comparison result as readable console text."""
    baseline = result["baseline"]
    target = result["target"]
    counts = build_counts(result)

    lines = [
        f"Comparison: {baseline['run_id']} → {target['run_id']}",
        f"Topic: {target['topic']} | Platform: {target['platform']}",
        "",
        "Sources:",
        f"  +{counts['sources_new']} new | "
        f"{counts['sources_repeated']} repeated | "
        f"-{counts['sources_disappeared']} disappeared",
        "Claims:",
        f"  +{counts['claims_new']} new | "
        f"{counts['claims_repeated']} repeated | "
        f"-{counts['claims_disappeared']} disappeared",
        "Narratives:",
        f"  +{counts['narratives_new']} new | "
        f"{counts['narratives_repeated']} repeated | "
        f"-{counts['narratives_disappeared']} disappeared",
        f"  ↑{counts['narratives_strengthened']} strengthened | "
        f"↓{counts['narratives_weakened']} weakened",
    ]

    if result["trends"]:
        lines.append("")
        lines.append("Trend Signals:")
        for t in result["trends"][:5]:
            lines.append(f"  [{t['signal_type']}] {t['title']} (score: {t['score']:.2f})")

    if result["follow_ups"]:
        lines.append("")
        lines.append("Follow-ups:")
        for f in result["follow_ups"]:
            lines.append(f"  - {f}")

    return "\n".join(lines)


def build_follow_ups(result: ComparisonResult) -> list[str]:
    """Generate research follow-up suggestions from comparison."""
    suggestions: list[str] = []

    for n in result["narrative_changes"]:
        if n["status"] == "new" and len(suggestions) < _MAX_FOLLOW_UPS:
            suggestions.append(f"Investigate emerging narrative: {n['title']}")

    corr_changed = [
        c
        for c in result["claim_changes"]
        if c["status"] == "repeated" and c["corroboration_changed"]
    ]
    if corr_changed:
        suggestions.append(f"Review {len(corr_changed)} claims with changed corroboration status")

    for n in result["narrative_changes"]:
        if n.get("strength_signal") == "weakened" and len(suggestions) < _MAX_FOLLOW_UPS:
            suggestions.append(f"Monitor weakening narrative: {n['title']}")

    new_sources = sum(1 for s in result["source_changes"] if s["status"] == "new")
    if new_sources > 0 and len(suggestions) < _MAX_FOLLOW_UPS:
        suggestions.append(f"Assess {new_sources} newly discovered sources")

    return suggestions[:_MAX_FOLLOW_UPS]
