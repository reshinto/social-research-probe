from __future__ import annotations

import math
import os
import statistics
from datetime import UTC, datetime
from typing import Literal

from social_research_probe.commands.parse import ParsedRunResearch
from social_research_probe.errors import ValidationError
from social_research_probe.llm.host import emit_packet
from social_research_probe.platforms.base import FetchLimits
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.purposes import registry as purpose_registry
from social_research_probe.purposes.merge import merge_purposes
from social_research_probe.scoring.combine import overall_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.trend import trend_score
from social_research_probe.scoring.trust import trust_score
from social_research_probe.synthesize.formatter import build_packet
from social_research_probe.validation.source import classify as classify_source

Mode = Literal["skill", "cli"]

_SRC_NUM = {"primary": 1.0, "secondary": 0.7, "commentary": 0.4, "unknown": 0.3}

_STOPWORDS = frozenset({
    "the", "a", "an", "of", "for", "to", "and", "or", "in", "on", "with",
    "get", "my", "by", "via", "from", "about", "how", "what", "which", "track",
    "latest", "across", "channels", "velocity", "saturation", "emergence",
})


def _enrich_query(topic: str, method: str) -> str:
    words = [w for w in method.lower().split() if w not in _STOPWORDS and len(w) > 2][:3]
    extra = " ".join(dict.fromkeys(words))  # dedupe preserving order
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
        import tests.fixtures.fake_youtube  # noqa: F401


def _score_item(it, sig, h, z_vel: float, z_eng: float):
    src = classify_source(it, h)
    trust = trust_score(
        source_class=_SRC_NUM[src.value],
        channel_credibility=_channel_credibility(h.subscriber_count),
        citation_traceability=min(1.0, len(h.citation_markers) / 3),
        ai_slop_penalty=0.0,
        corroboration_score=0.3,
    )
    age_days = max(1.0, (datetime.now(UTC) - sig.upload_date).days if sig.upload_date else 30.0)
    trend = trend_score(
        z_view_velocity=z_vel,
        z_engagement_ratio=z_eng,
        z_cross_channel_repetition=sig.cross_channel_repetition or 0.0,
        age_days=age_days,
    )
    engagement = sig.engagement_ratio or 0.0
    opp = opportunity_score(
        market_gap=max(0.0, 1.0 - (sig.cross_channel_repetition or 0.0)),
        monetization_proxy=min(1.0, engagement * 20),
        feasibility=0.5,
        novelty=max(0.0, 1.0 - age_days / 180.0),
    )
    ov = overall_score(trust=trust, trend=trend, opportunity=opp)
    return ov, {
        "title": it.title,
        "channel": it.author_name,
        "url": it.url,
        "source_class": src.value,
        "scores": {"trust": trust, "trend": trend, "opportunity": opp, "overall": ov},
        "one_line_takeaway": (it.text_excerpt or it.title)[:140],
    }


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
            _score_item(it, s, h, zv, ze)
            for it, s, h, zv, ze in zip(items, signals, hints, z_vels, z_engs, strict=True)
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
            "notes": "",
        }
        packets.append(build_packet(
            topic=topic,
            platform=cmd.platform,
            purpose_set=list(merged.names),
            items_top5=top5,
            source_validation_summary=svs,
            platform_signals_summary=f"{len(items)} items fetched",
            evidence_summary=(
                "deterministic fixture"
                if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE")
                else "live fetch"
            ),
            stats_summary={"models_run": [], "highlights": [], "low_confidence": True},
            chart_captions=[],
            warnings=[],
        ))

    combined = (
        packets[0]
        if len(packets) == 1
        else {"multi": packets, "response_schema": packets[0]["response_schema"]}
    )
    if mode == "skill":
        emit_packet(combined, kind="synthesis")  # exits 0
    return combined
