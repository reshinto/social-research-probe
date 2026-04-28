"""Re-export shim — logic lives in utils/report/formatter.py."""

from social_research_probe.utils.report.formatter import (  # noqa: F401
    _contextual_explanation,
    _ensure_sentence,
    _highlights_table,
    _infer_model,
    _markdown_to_plain_text,
    _plain_list_sentences,
    _plain_sentences,
    _render_timing_footer,
    _summary_sentences,
    _to_bullets,
    _usable_summary_text,
    build_fallback_report_summary,
    build_report,
    render_full,
    render_sections_1_9,
    resolve_report_summary,
)

_bulletise = _to_bullets

__all__ = [
    "build_fallback_report_summary",
    "build_report",
    "render_full",
    "render_sections_1_9",
    "resolve_report_summary",
]
