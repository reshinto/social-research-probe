"""Item scoring: credibility, z-scores, per-item score assembly."""

from __future__ import annotations

import math
import statistics
from datetime import UTC, datetime

from social_research_probe.platforms.base import RawItem, SignalSet, TrustHints
from social_research_probe.scoring.combine import overall_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.trend import trend_score
from social_research_probe.scoring.trust import trust_score
from social_research_probe.types import ScoredItem
from social_research_probe.validation.source import classify as classify_source

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


def _score_item(
    item: RawItem,
    signal: SignalSet,
    hints: TrustHints,
    z_view_velocity: float,
    z_engagement: float,
) -> tuple[float, ScoredItem]:
    src = classify_source(item, hints)
    trust = trust_score(
        source_class=_SRC_NUM[src.value],
        channel_credibility=_channel_credibility(hints.subscriber_count),
        citation_traceability=min(1.0, len(hints.citation_markers) / 3),
        ai_slop_penalty=0.0,
        corroboration_score=0.3,
    )
    age_days = max(
        1.0,
        (datetime.now(UTC) - signal.upload_date).days if signal.upload_date else 30.0,
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
        "scores": {
            "trust": trust,
            "trend": trend,
            "opportunity": opportunity,
            "overall": overall,
        },
        "features": {
            "view_velocity": signal.view_velocity or 0.0,
            "engagement_ratio": signal.engagement_ratio or 0.0,
            "age_days": age_days,
            "subscriber_count": float(hints.subscriber_count or 0),
        },
        "one_line_takeaway": (item.text_excerpt or item.title)[:140],
    }
