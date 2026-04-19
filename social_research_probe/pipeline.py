from __future__ import annotations

import math
import os
import statistics
from datetime import UTC, datetime
from typing import Literal

from social_research_probe.commands.parse import ParsedRunResearch
from social_research_probe.errors import ValidationError
from social_research_probe.llm.host import emit_packet
from social_research_probe.platforms.base import FetchLimits, RawItem, SignalSet, TrustHints
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.purposes import registry as purpose_registry
from social_research_probe.purposes.merge import merge_purposes
from social_research_probe.scoring.combine import overall_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.trend import trend_score
from social_research_probe.scoring.trust import trust_score
from social_research_probe.stats.selector import select_and_run
from social_research_probe.synthesize.evidence import summarize as summarize_evidence
from social_research_probe.synthesize.evidence import summarize_signals
from social_research_probe.synthesize.formatter import build_packet
from social_research_probe.validation.source import classify as classify_source
from social_research_probe.viz.selector import select_and_render

Mode = Literal["skill", "cli"]

_SRC_NUM = {"primary": 1.0, "secondary": 0.7, "commentary": 0.4, "unknown": 0.3}

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "for",
        "to",
        "and",
        "or",
        "in",
        "on",
        "with",
        "get",
        "my",
        "by",
        "via",
        "from",
        "about",
        "how",
        "what",
        "which",
        "track",
        "latest",
        "across",
        "channels",
        "velocity",
        "saturation",
        "emergence",
    }
)


def _enrich_query(topic: str, method: str) -> str:
    words = [w for w in method.lower().split() if w not in _STOPWORDS and len(w) > 2][:3]
    extra = " ".join(dict.fromkeys(words))
    return f"{topic} {extra}".strip() if extra else topic


def _channel_credibility(subscriber_count: int | None) -> float:
    if not subscriber_count:
        return 0.3
    return min(1.0, 0.15 * math.log10(max(1, subscriber_count)))


def _zscore(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mu = statistics.mean(values)
    sd = statistics.stdev(values) or 1.0
    return [(v - mu) / sd for v in values]


def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import importlib

        importlib.import_module("tests.fixtures.fake_youtube")


def _score_item(
    item: RawItem,
    signal: SignalSet,
    hints: TrustHints,
    z_view_velocity: float,
    z_engagement: float,
) -> tuple[float, dict]:
    src = classify_source(item, hints)
    trust = trust_score(
        source_class=_SRC_NUM[src.value],
        channel_credibility=_channel_credibility(hints.subscriber_count),
        citation_traceability=min(1.0, len(hints.citation_markers) / 3),
        ai_slop_penalty=0.0,
        corroboration_score=0.3,
    )
    age_days = max(
        1.0, (datetime.now(UTC) - signal.upload_date).days if signal.upload_date else 30.0
    )
    trend = trend_score(
        z_view_velocity=z_view_velocity,
        z_engagement_ratio=z_engagement,
        z_cross_channel_repetition=signal.cross_channel_repetition or 0.0,
        age_days=age_days,
    )
    engagement = signal.engagement_ratio or 0.0
    opportunity = opportunity_score(
        market_gap=max(0.0, 1.0 - (signal.cross_channel_repetition or 0.0)),
        monetization_proxy=min(1.0, engagement * 20),
        feasibility=0.5,
        novelty=max(0.0, 1.0 - age_days / 180.0),
    )
    overall = overall_score(trust=trust, trend=trend, opportunity=opportunity)
    return overall, {
        "title": item.title,
        "channel": item.author_name,
        "url": item.url,
        "source_class": src.value,
        "scores": {"trust": trust, "trend": trend, "opportunity": opportunity, "overall": overall},
        "one_line_takeaway": (item.text_excerpt or item.title)[:140],
    }


def _build_stats_summary(scores: list[float]) -> dict:
    """Run the stats selector on overall scores and shape it for the packet."""
    results = select_and_run(scores, label="overall_score")
    models_run = ["descriptive"] if scores else []
    if len(scores) >= 3:
        models_run.append("growth")
    return {
        "models_run": models_run,
        "highlights": [r.caption for r in results],
        "low_confidence": len(scores) < 3,
    }


def _render_charts(scores: list[float], data_dir) -> list[str]:
    """Render an overall-score chart into ``<data_dir>/charts/`` if data exists."""
    if not scores:
        return []
    charts_dir = data_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart = select_and_render(scores, label="overall_score", output_dir=str(charts_dir))
    return [chart.caption]


def run_research(cmd: ParsedRunResearch, data_dir, mode: Mode) -> dict:
    _maybe_register_fake()
    purposes = purpose_registry.load(data_dir)["purposes"]
    adapter = get_adapter(cmd.platform, {"data_dir": data_dir})
    if not adapter.health_check():
        raise ValidationError(f"adapter {cmd.platform} failed health check")

    packets: list[dict] = []
    for topic, purpose_names in cmd.topics:
        for n in purpose_names:
            if n not in purposes:
                raise ValidationError(f"unknown purpose: {n!r}")
        merged = merge_purposes(purposes, list(purpose_names))
        search_topic = _enrich_query(topic, merged.method)
        items = adapter.enrich(adapter.search(search_topic, FetchLimits()))
        signals = adapter.to_signals(items)
        hints = [adapter.trust_hints(it) for it in items]
        z_vels = _zscore([s.view_velocity or 0.0 for s in signals])
        z_engs = _zscore([s.engagement_ratio or 0.0 for s in signals])
        scored = [
            _score_item(item, signal, hint, z_vel, z_eng)
            for item, signal, hint, z_vel, z_eng in zip(
                items, signals, hints, z_vels, z_engs, strict=True
            )
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        top5 = [d for _, d in scored[:5]]
        svs = {
            "validated": 0,
            "partially": 0,
            "unverified": len(top5),
            "low_trust": sum(1 for d in top5 if d["scores"]["trust"] < 0.4),
            "primary": sum(1 for d in top5 if d["source_class"] == "primary"),
            "secondary": sum(1 for d in top5 if d["source_class"] == "secondary"),
            "commentary": sum(1 for d in top5 if d["source_class"] == "commentary"),
            "notes": "corroboration not run; use 'srp corroborate-claims' for validation",
        }
        overall_scores = [d["scores"]["overall"] for d in top5]
        stats_summary = _build_stats_summary(overall_scores)
        chart_captions = _render_charts(overall_scores, data_dir)
        packets.append(
            build_packet(
                topic=topic,
                platform=cmd.platform,
                purpose_set=list(merged.names),
                items_top5=top5,
                source_validation_summary=svs,
                platform_signals_summary=summarize_signals(signals),
                evidence_summary=summarize_evidence(items, signals, top5),
                stats_summary=stats_summary,
                chart_captions=chart_captions,
                warnings=[],
            )
        )

    combined = (
        packets[0]
        if len(packets) == 1
        else {"multi": packets, "response_schema": packets[0]["response_schema"]}
    )
    if mode == "skill":
        emit_packet(combined, kind="synthesis")  # exits 0
    return combined
