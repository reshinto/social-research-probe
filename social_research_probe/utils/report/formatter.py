"""Report formatting and Markdown rendering for srp research output.

Transforms a raw research report (produced by the pipeline) into a
human-readable Markdown report. Also builds the canonical research report dict.

The deterministic report body comes from report data. Compiled Synthesis,
Opportunity Analysis, and Final Summary come from the report when available;
Final Summary falls back to a deterministic summary built from existing report
data when synthesis is disabled.
"""

from __future__ import annotations

import re
from functools import lru_cache

from social_research_probe.utils.core.types import (
    ResearchReport,
    ScoredItem,
    SourceValidationSummary,
    StatsSummary,
)
from social_research_probe.utils.report.contextual_explain import (
    contextual_explanation as _contextual_explanation,
)
from social_research_probe.utils.report.contextual_explain import infer_model as _infer_model

__all__ = [
    "build_fallback_report_summary",
    "build_report",
    "render_full",
    "render_sections_1_9",
    "resolve_report_summary",
]

_UNAVAILABLE_SUMMARY_MARKERS = (
    "LLM synthesis unavailable",
    "LLM summary unavailable",
)


def build_report(
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
) -> ResearchReport:
    """Build build report in the shape consumed by the next project step.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        topic: Research topic text or existing topic list used for classification and suggestions.
        platform: Platform name, such as youtube or all, used to select config and pipeline
                  behavior.
        purpose_set: Purpose names attached to the report or persisted run.
        items_top_n: Top-ranked source items carried into the final report.
                source_validation_summary: Source validation counts and labels included in the report.
                platform_engagement_summary: Platform engagement narrative included in the report.
        evidence_summary: Evidence summary value that changes the behavior described by this
                          helper.
        stats_summary: Statistical summary records shown in the report.
        chart_captions: Chart captions shown next to rendered chart artifacts.
        warnings: Warning or penalty records that explain reduced evidence quality.
        chart_takeaways: Chart takeaways value that changes the behavior described by this
                         helper.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            build_report(
                topic="AI safety",
                platform="AI safety",
                purpose_set=["AI safety"],
                items_top_n=["AI safety"],
                source_validation_summary="AI safety",
                platform_engagement_summary="AI safety",
                evidence_summary="AI safety",
                stats_summary="AI safety",
                chart_captions=["AI safety"],
                warnings=["Transcript unavailable"],
                chart_takeaways=["AI safety"],
            )
        Output:
            "AI safety"
    """
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
    """Render the top items as a markdown table for compact scanning.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _items_table(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            "AI safety"
    """
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
    """Render per-item URL and takeaway as a bullet list below the score table.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _items_links_and_takeaways(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            "AI safety"
    """
    bullets = []
    for i, it in enumerate(items, start=1):
        bullets.append(
            f"- **[{i}]** [{it['channel']}]({it['url']}) — {it.get('one_line_takeaway', '')}"
        )
    return "\n".join(bullets)


def _highlights_table(highlights: list[str]) -> str:
    """Render stat highlights as a four-column markdown table.

    Columns: Model | Metric | Finding | What it means The Model column is left blank for
    consecutive rows of the same model to visually group related metrics. The 'What it
    means' column is generated dynamically from the actual metric value, not a static
    definition.

    Args:
        highlights: HTML, caption, metric, or report text being formatted for the final report.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _highlights_table(
                highlights="Engagement increased",
            )
        Output:
            "AI safety"
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
    """Split a semicolon-separated summary string into a markdown bullet list.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _to_bullets(
                text="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    return "\n".join(f"- {part.strip()}" for part in text.split(";") if part.strip())


_bulletise = _to_bullets


def render_full(
    report: ResearchReport,
) -> str:
    """Render the full Markdown report from report data and synthesis text.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            render_full(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    body = render_sections_1_9(report)
    compiled_synthesis_text = (
        report.get("compiled_synthesis")
        or "_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    opportunity_analysis_text = (
        report.get("opportunity_analysis")
        or "_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    final_summary_text = (
        resolve_report_summary(report)
        or "_(LLM summary unavailable — runner disabled or all runners failed; see terminal logs)_"
    )
    body += f"\n## 10. Compiled Synthesis\n\n{compiled_synthesis_text}\n"
    body += f"\n## 11. Opportunity Analysis\n\n{opportunity_analysis_text}\n"
    body += f"\n## 12. Final Summary\n\n{final_summary_text}\n"
    footer = _render_timing_footer(report.get("stage_timings", []))
    if footer:
        body += f"\n{footer}\n"
    return body


def _render_timing_footer(timings: list) -> str:
    """Return a one-line italic timing summary, or empty when no stages recorded.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        timings: Stage timing records used in methodology output.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _render_timing_footer(
                timings=["AI safety"],
            )
        Output:
            "AI safety"
    """
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


def render_sections_1_9(report: ResearchReport) -> str:
    """Render sections 1-9 deterministically from report data.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            render_sections_1_9(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    svs = report.get("source_validation_summary") or {}
    items = report["items_top_n"]
    stats = report["stats_summary"]
    warnings = report.get("warnings", [])
    parts: list[str] = []
    parts.append(
        "## 1. Topic & Purpose\n\n"
        f"- **Topic:** {report['topic']}\n"
        f"- **Purposes:** {', '.join(report['purpose_set'])}"
    )
    parts.append(f"## 2. Platform\n\n- **Platform:** {report['platform']}")
    if items:
        parts.append(
            "## 3. Top Items\n\n"
            + _items_table(items)
            + "\n\n**Links & takeaways:**\n\n"
            + _items_links_and_takeaways(items)
        )
    else:
        parts.append("## 3. Top Items\n\n_(no items returned)_")
    parts.append("## 4. Platform Signals\n\n" + _to_bullets(report["platform_engagement_summary"]))
    parts.append(
        "## 5. Source Validation\n\n"
        f"- validated: {svs.get('validated', 0)}, partial: {svs.get('partially', 0)}, "
        f"unverified: {svs.get('unverified', 0)}, low-trust: {svs.get('low_trust', 0)}\n"
        f"- primary/secondary/commentary: {svs.get('primary', 0)}/{svs.get('secondary', 0)}/{svs.get('commentary', 0)}"
        + (f"\n- notes: {svs['notes']}" if svs.get("notes") else "")
    )
    parts.append("## 6. Evidence\n\n" + _to_bullets(report["evidence_summary"]))
    lc = "\n\n_low confidence — interpret with caution_" if stats.get("low_confidence") else ""
    highlights = stats.get("highlights", [])
    parts.append(f"## 7. Statistics\n\n{_highlights_table(highlights)}{lc}")
    caps = report.get("chart_captions", [])
    parts.append("## 8. Charts\n\n" + ("\n\n".join(caps) if caps else "_(no charts rendered)_"))
    parts.append(
        "## 9. Warnings\n\n" + ("\n".join(f"- {w}" for w in warnings) if warnings else "_(none)_")
    )
    return "\n\n".join(parts) + "\n"


def resolve_report_summary(report: ResearchReport) -> str | None:
    """Return the best available section-12 summary for *report*.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            resolve_report_summary(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    report_summary = _usable_summary_text(report.get("report_summary"))
    if report_summary:
        return report_summary
    return build_fallback_report_summary(report)


def build_fallback_report_summary(report: ResearchReport) -> str | None:
    """Build a non-LLM final summary from existing report data.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            build_fallback_report_summary(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    sentences: list[str] = []
    topic = str(report.get("topic", "") or "").strip()
    platform = str(report.get("platform", "") or "").strip()
    if topic and platform:
        sentences.append(f"This report covers {topic} on {platform}.")
    elif topic:
        sentences.append(f"This report covers {topic}.")

    source_validation = report.get("source_validation_summary", {})
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

    compiled = _plain_sentences(report.get("compiled_synthesis"), limit=1)
    if compiled:
        sentences.append("Compiled synthesis: " + " ".join(compiled))

    opportunity = _plain_sentences(report.get("opportunity_analysis"), limit=1)
    if opportunity:
        sentences.append("Opportunity analysis: " + " ".join(opportunity))

    stats_summary = report.get("stats_summary", {})
    highlights = _plain_list_sentences(list(stats_summary.get("highlights", []) or []), limit=2)
    if highlights:
        sentences.append("Statistics highlights: " + " ".join(highlights))
    elif stats_summary.get("low_confidence"):
        sentences.append("Statistics are low confidence because the sample is small.")

    chart_takeaways = _plain_list_sentences(list(report.get("chart_takeaways", []) or []), limit=2)
    if chart_takeaways:
        sentences.append("Chart signals: " + " ".join(chart_takeaways))

    signal_summary = _summary_sentences(report.get("platform_engagement_summary", ""), limit=2)
    if signal_summary:
        sentences.append("Platform engagement: " + " ".join(signal_summary))

    evidence_summary = _summary_sentences(report.get("evidence_summary", ""), limit=2)
    if evidence_summary:
        sentences.append("Evidence summary: " + " ".join(evidence_summary))

    warnings = _plain_list_sentences(list(report.get("warnings", []) or []), limit=1)
    if warnings:
        sentences.append("Cautions: " + " ".join(warnings))

    if not sentences:
        return None
    return " ".join(sentences)


def _usable_summary_text(value: object) -> str:
    """Return a clean stored summary value, filtering known placeholders.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _usable_summary_text(
                value="42",
            )
        Output:
            "AI safety"
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if any(marker in text for marker in _UNAVAILABLE_SUMMARY_MARKERS):
        return ""
    return text


@lru_cache(maxsize=128)
def _markdown_to_plain_text(text: str) -> str:
    """Collapse markdown-ish text into plain prose.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _markdown_to_plain_text(
                text="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
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
    """Return up to *limit* cleaned sentences from markdown-ish text.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.
        limit: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _plain_sentences(
                value="42",
                limit=3,
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Return up to *limit* cleaned sentences from a list of text fragments.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        values: User-provided values to validate and normalize.
        limit: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _plain_list_sentences(
                values=["AI safety", "model evaluation"],
                limit=3,
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    sentences: list[str] = []
    for value in values:
        for sentence in _plain_sentences(value, limit=1):
            sentences.append(sentence)
            if len(sentences) >= limit:
                return sentences
    return sentences


def _summary_sentences(text: str | None, *, limit: int) -> list[str]:
    """Return up to *limit* sentences from a semicolon-separated report summary.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        limit: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _summary_sentences(
                text="This tool reduces latency by 30%.",
                limit=3,
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    raw = _usable_summary_text(text)
    if not raw:
        return []
    parts = [part.strip() for part in raw.split(";") if part.strip()]
    return [_ensure_sentence(_markdown_to_plain_text(part)) for part in parts[:limit]]


def _ensure_sentence(text: str) -> str:
    """Ensure summary text ends with sentence punctuation.

    Report utilities keep fallback wording and formatting rules consistent between HTML, exports,
    and CLI summaries.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _ensure_sentence(
                text="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        return cleaned + "."
    return cleaned
