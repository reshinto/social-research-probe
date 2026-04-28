"""Re-export shim — logic lives in utils/report/formatter.py."""

from social_research_probe.utils.report.formatter import (
    _ensure_sentence,
    _highlights_table,
    _items_links_and_takeaways,
    _items_table,
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

__all__ = [
    "_ensure_sentence",
    "_highlights_table",
    "_items_links_and_takeaways",
    "_items_table",
    "_markdown_to_plain_text",
    "_plain_list_sentences",
    "_plain_sentences",
    "_render_timing_footer",
    "_summary_sentences",
    "_to_bullets",
    "_usable_summary_text",
    "build_fallback_report_summary",
    "build_report",
    "render_full",
    "render_sections_1_9",
    "resolve_report_summary",
]
