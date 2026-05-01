from __future__ import annotations

import math
import statistics as _statistics
from datetime import UTC, datetime
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.technologies.scoring.combine import overall_score
from social_research_probe.technologies.scoring.opportunity import opportunity_score
from social_research_probe.technologies.scoring.trend import trend_score
from social_research_probe.technologies.scoring.trust import trust_score
from social_research_probe.utils.core.types import EngagementMetrics, RawItem


def zscores(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mu = _statistics.mean(values)
    sd = _statistics.stdev(values) or 1.0
    return [(v - mu) / sd for v in values]


def channel_credibility(subscribers: int | None) -> float:
    if not subscribers:
        return 0.3
    return min(1.0, 0.15 * math.log10(max(1, subscribers)))


def age_days(published: object) -> float:
    if not isinstance(published, datetime):
        return 30.0
    return max(1.0, float((datetime.now(UTC) - published).days))


def normalize_item(item: object) -> dict | None:
    if isinstance(item, dict):
        return item
    if not isinstance(item, RawItem):
        return None
    return {
        "id": item.id,
        "url": item.url,
        "title": item.title,
        "channel": item.author_name,
        "author_id": item.author_id,
        "author_name": item.author_name,
        "published_at": item.published_at,
        # Keep metadata text/media available after scoring so enrichment can build a
        # useful text surrogate even when no transcript is fetched.
        "text_excerpt": item.text_excerpt,
        "thumbnail": item.thumbnail,
        "extras": dict(item.extras) if item.extras else {},
    }


def normalize_with_metrics(
    items: list, engagement_metrics: list
) -> tuple[list[dict], list[EngagementMetrics | None]]:
    normalized: list[dict] = []
    aligned: list[EngagementMetrics | None] = []
    for idx, item in enumerate(items):
        n = normalize_item(item)
        if n is None:
            continue
        normalized.append(n)
        aligned.append(engagement_metrics[idx] if idx < len(engagement_metrics) else None)
    return normalized, aligned


def compute_trust(extras: dict) -> float:
    return trust_score(
        source_class=0.4,
        channel_credibility=channel_credibility(extras.get("channel_subscribers")),
        citation_traceability=0.3,
        ai_slop_penalty=0.0,
        corroboration_score=0.3,
    )


def compute_trend(z_velocity: float, z_engagement: float, cross_rep: float, age: float) -> float:
    return trend_score(
        z_view_velocity=z_velocity,
        z_engagement_ratio=z_engagement,
        z_cross_channel_repetition=cross_rep,
        age_days=age,
    )


def compute_opportunity(engagement: float, cross_rep: float, age: float) -> float:
    return opportunity_score(
        market_gap=max(0.0, 1.0 - cross_rep),
        monetization_proxy=min(1.0, engagement * 20),
        feasibility=0.5,
        novelty=max(0.0, 1.0 - age / 180.0),
    )


def build_features(velocity: float, engagement: float, age: float, subscribers: int | None) -> dict:
    return {
        "view_velocity": velocity,
        "engagement_ratio": engagement,
        "age_days": age,
        "subscriber_count": float(subscribers or 0),
    }


def _metric_values(metrics: EngagementMetrics | None) -> tuple[float, float, float]:
    if metrics is None:
        return 0.0, 0.0, 0.0
    return (
        metrics.view_velocity or 0.0,
        metrics.engagement_ratio or 0.0,
        metrics.cross_channel_repetition or 0.0,
    )


def score_one(
    item: dict,
    metrics: EngagementMetrics | None,
    z_velocity: float,
    z_engagement: float,
    weights,
) -> dict:
    extras = item.get("extras") or {}
    velocity, engagement, cross_rep = _metric_values(metrics)
    age = age_days(item.get("published_at"))
    trust = compute_trust(extras)
    trend = compute_trend(z_velocity, z_engagement, cross_rep, age)
    opportunity = compute_opportunity(engagement, cross_rep, age)
    overall = overall_score(trust=trust, trend=trend, opportunity=opportunity, weights=weights)
    return {
        **item,
        "source_class": item.get("source_class") or "unknown",
        "scores": {
            "trust": trust,
            "trend": trend,
            "opportunity": opportunity,
            "overall": overall,
        },
        "features": build_features(velocity, engagement, age, extras.get("channel_subscribers")),
    }


def score_items(items: list, engagement_metrics: list, weights=None) -> list[dict]:
    """Compute trust/trend/opportunity/overall per item and rank descending."""
    normalized, aligned = normalize_with_metrics(items, engagement_metrics)
    if not normalized:
        return []
    velocities = [_metric_values(m)[0] for m in aligned]
    engagements = [_metric_values(m)[1] for m in aligned]
    zv = zscores(velocities)
    ze = zscores(engagements)
    scored = [score_one(n, aligned[i], zv[i], ze[i], weights) for i, n in enumerate(normalized)]
    scored.sort(key=lambda d: d.get("scores", {}).get("overall", 0.0), reverse=True)
    return scored


class ScoringComputeTech(BaseTechnology[object, list]):
    """Technology wrapper for computing full scores for a batch of items."""

    name: ClassVar[str] = "scoring.compute"
    enabled_config_key: ClassVar[str] = "scoring_compute"

    async def _execute(self, input_data: object) -> list:
        items = input_data.get("items", []) if isinstance(input_data, dict) else []
        metrics = input_data.get("engagement_metrics", []) if isinstance(input_data, dict) else []
        weights = input_data.get("weights", {}) if isinstance(input_data, dict) else None
        return score_items(items, metrics, weights)
