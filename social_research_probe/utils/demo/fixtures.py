"""Synthetic ResearchReport assembler for the offline demo report command.

Combines build_demo_items() with synthetic top-level fields into a complete
ResearchReport ready to pass through ReportService and ExportService unchanged.
The disclaimer is injected into warnings, compiled_synthesis, report_summary,
and the topic prefix so every artifact surfaces the synthetic-data marker
through the existing renderers. No I/O.
"""

from __future__ import annotations

from collections import Counter

from social_research_probe.utils.core.types import (
    ResearchReport,
    ScoredItem,
    SourceValidationSummary,
    StatsSummary,
)
from social_research_probe.utils.demo.constants import (
    DEMO_DISCLAIMER,
    DEMO_PURPOSE_SET,
    DEMO_THEMES,
    DEMO_TOPIC,
)
from social_research_probe.utils.demo.items import build_demo_items

_VERIFIED = "verified"
_PARTIAL = "partially_verified"


def _source_validation_summary(items: list[ScoredItem]) -> SourceValidationSummary:
    classes = Counter(item.get("source_class", "unknown") for item in items)
    verdicts = Counter(item.get("corroboration_verdict", "unverified") for item in items)
    low_trust = sum(1 for item in items if item.get("scores", {}).get("trust", 0.0) < 0.4)
    return {
        "validated": verdicts.get(_VERIFIED, 0),
        "partially": verdicts.get(_PARTIAL, 0),
        "unverified": verdicts.get("unverified", 0),
        "low_trust": low_trust,
        "primary": classes.get("primary", 0),
        "secondary": classes.get("secondary", 0),
        "commentary": classes.get("commentary", 0),
        "notes": (
            "Synthetic distribution covers four source-class buckets. "
            "Counts are illustrative; do not interpret as real coverage."
        ),
    }


def _stats_summary() -> StatsSummary:
    return {
        "models_run": [],
        "highlights": [
            f"Synthetic highlight on {DEMO_THEMES[0]}.",
            f"Synthetic highlight on {DEMO_THEMES[1]}.",
            f"Synthetic highlight on {DEMO_THEMES[2]}.",
        ],
        "low_confidence": False,
    }


def _chart_captions() -> list[str]:
    return [
        "Synthetic chart: trust vs. trend distribution across 12 demo items.",
        "Synthetic chart: comment volume per source class.",
        "Synthetic chart: evidence-tier coverage of the demo sample.",
    ]


def _chart_takeaways() -> list[str]:
    return [
        f"{DEMO_DISCLAIMER} Trust scores cluster around primary-class items.",
        f"Comment engagement concentrates on {DEMO_THEMES[1]}.",
        "Evidence tiers are balanced across the synthetic sample.",
    ]


def _compiled_synthesis() -> str:
    return (
        f"{DEMO_DISCLAIMER} The demo report illustrates how a real run "
        f"surfaces narrative themes such as {DEMO_THEMES[0]}, "
        f"{DEMO_THEMES[1]}, and {DEMO_THEMES[2]} across mixed-quality "
        "sources. All numbers, quotes, and channel names are fabricated."
    )


def _opportunity_analysis() -> str:
    return (
        f"{DEMO_DISCLAIMER} Opportunity framing in a real run would weigh "
        f"signal strength against source credibility; here the framing "
        f"showcases {DEMO_THEMES[2]} and {DEMO_THEMES[3]} as illustrative "
        "high-leverage areas without making factual claims."
    )


def _report_summary() -> str:
    return (
        f"{DEMO_DISCLAIMER} This summary demonstrates the layout of the "
        "executive overview block produced by a normal research run."
    )


def _platform_engagement_summary() -> str:
    return (
        f"{DEMO_DISCLAIMER} Engagement figures across the 12 synthetic "
        "items mimic the spread observed in real YouTube research runs."
    )


def _evidence_summary() -> str:
    return (
        f"{DEMO_DISCLAIMER} Evidence coverage spans metadata-only items "
        "through full transcript-plus-comment-plus-external corroboration."
    )


def _warnings() -> list[str]:
    return [
        DEMO_DISCLAIMER,
        "YouTube sample skewed to English-language uploads.",
        "transcript_status=failed for 1 item due to provider rate limit.",
    ]


def _stage_timings() -> list[dict]:
    return [
        {"stage": "fetch", "elapsed_s": 1.42, "status": "ok"},
        {"stage": "score", "elapsed_s": 0.31, "status": "ok"},
        {"stage": "enrich", "elapsed_s": 2.18, "status": "ok"},
        {"stage": "report", "elapsed_s": 0.74, "status": "ok"},
    ]


def build_demo_report() -> ResearchReport:
    """Build a complete synthetic ResearchReport for the offline demo command."""
    items = build_demo_items()
    report: ResearchReport = {
        "topic": DEMO_TOPIC,
        "platform": "youtube",
        "purpose_set": list(DEMO_PURPOSE_SET),
        "items_top_n": items,
        "source_validation_summary": _source_validation_summary(items),
        "platform_engagement_summary": _platform_engagement_summary(),
        "evidence_summary": _evidence_summary(),
        "stats_summary": _stats_summary(),
        "chart_captions": _chart_captions(),
        "chart_takeaways": _chart_takeaways(),
        "warnings": _warnings(),
        "stage_timings": _stage_timings(),
        "compiled_synthesis": _compiled_synthesis(),
        "opportunity_analysis": _opportunity_analysis(),
        "report_summary": _report_summary(),
    }
    return report
