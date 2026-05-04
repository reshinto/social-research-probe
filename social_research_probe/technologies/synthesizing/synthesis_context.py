"""Pass-through transformer: ResearchReport → SynthesisContext for the LLM.

The final synthesis LLM only sees this compact, normalised shape. It contains
nothing the report didn't already have — all interpretation work (stats
highlights, chart takeaways, corroboration verdicts, divergence warnings) has
already been computed deterministically upstream. Every field tolerates being
missing so disabled features silently produce empty sections.
"""

from __future__ import annotations

from social_research_probe.utils.core.types import (
    Coverage,
    ResearchReport,
    ScoredItem,
    SynthesisContext,
    SynthesisItem,
)


def build_synthesis_context(report: ResearchReport) -> SynthesisContext:
    """Build build synthesis context in the shape consumed by the next project step.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            build_synthesis_context(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    items_top_n = list(report.get("items_top_n", []))
    return SynthesisContext(
        topic=str(report.get("topic", "")),
        platform=str(report.get("platform", "")),
        coverage=_build_coverage(report, items_top_n),
        items=[_build_item(i, item) for i, item in enumerate(items_top_n)],
        source_validation_summary=report.get(
            "source_validation_summary",
            {
                "validated": 0,
                "partially": 0,
                "unverified": 0,
                "low_trust": 0,
                "primary": 0,
                "secondary": 0,
                "commentary": 0,
                "notes": "",
            },
        ),
        platform_engagement_summary=str(report.get("platform_engagement_summary", "") or ""),
        evidence_summary=str(report.get("evidence_summary", "") or ""),
        stats_highlights=list(report.get("stats_summary", {}).get("highlights", []) or []),
        chart_takeaways=list(report.get("chart_takeaways", []) or []),
        warnings=list(report.get("warnings", []) or []),
    )


def _build_coverage(report: ResearchReport, items_top_n: list[ScoredItem]) -> Coverage:
    """Build the coverage structure consumed by the next step.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        items_top_n: Top-ranked source items carried into the final report.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _build_coverage(
                report={"topic": "AI safety", "items_top_n": []},
                items_top_n=["AI safety"],
            )
        Output:
            "AI safety"
    """
    platforms = [p for p in [str(report.get("platform", ""))] if p]
    stats = report.get("stats_summary", {})
    fetched_hint = _fetched_from_highlights(list(stats.get("highlights", []) or []))
    return Coverage(
        fetched=fetched_hint if fetched_hint is not None else len(items_top_n),
        enriched=len(items_top_n),
        platforms=platforms,
    )


def _fetched_from_highlights(highlights: list[str]) -> int | None:
    """Best-effort dig for an ``n=<int>`` token in stats highlights.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        highlights: HTML, caption, metric, or report text being formatted for the final report.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _fetched_from_highlights(
                highlights="Engagement increased",
            )
        Output:
            "AI safety"
    """
    for line in highlights:
        for token in line.split():
            if token.startswith("n=") and token[2:].rstrip(",").isdigit():
                return int(token[2:].rstrip(","))
    return None


def _build_item(index: int, item: ScoredItem) -> SynthesisItem:
    """Build build item in the shape consumed by the next project step.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        index: Count, database id, index, or limit that bounds the work being performed.
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _build_item(
                index=3,
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            "AI safety"
    """
    out: SynthesisItem = {
        "rank": index + 1,
        "title": str(item.get("title", "")),
        "url": str(item.get("url", "")),
    }
    scores = item.get("scores")
    if scores:
        out["scores"] = scores
    takeaway = item.get("one_line_takeaway")
    if takeaway:
        out["takeaway"] = takeaway
    summary = item.get("summary") or takeaway
    if summary:
        out["summary"] = summary
    verdict = item.get("corroboration_verdict")
    if isinstance(verdict, str) and verdict:
        out["corroboration"] = verdict
    return out
