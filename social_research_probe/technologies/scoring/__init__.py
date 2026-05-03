"""Technologies scoring support.

It keeps provider or algorithm details behind the adapter API used by services.
"""

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
from social_research_probe.utils.core.types import EngagementMetrics
from social_research_probe.utils.pipeline.helpers import normalize_item


def zscores(values: list[float]) -> list[float]:
    """Document the zscores rule at the boundary where callers use it.

    Args:
        values: User-provided values to validate and normalize.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            zscores(
                values=["AI safety", "model evaluation"],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    if len(values) < 2:
        return [0.0] * len(values)
    mu = _statistics.mean(values)
    sd = _statistics.stdev(values) or 1.0
    return [(v - mu) / sd for v in values]


def channel_credibility(subscribers: int | None) -> float:
    """Return the channel credibility.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        subscribers: Subscriber count used in source credibility scoring.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            channel_credibility(
                subscribers="AI safety",
            )
        Output:
            0.75
    """
    if not subscribers:
        return 0.3
    return min(1.0, 0.15 * math.log10(max(1, subscribers)))


def age_days(published: object) -> float:
    """Return the age days.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        published: Timestamp used for recency filtering, age calculations, or persisted audit
                   metadata.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            age_days(
                published="2026-01-01T00:00:00Z",
            )
        Output:
            0.75
    """
    if not isinstance(published, datetime):
        return 30.0
    return max(1.0, float((datetime.now(UTC) - published).days))


def normalize_with_metrics(
    items: list, engagement_metrics: list
) -> tuple[list[dict], list[EngagementMetrics | None]]:
    """Normalize with metrics into a serializable value.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            normalize_with_metrics(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                engagement_metrics={"views": 1200, "likes": 80},
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Compute trust from normalized metrics.

    Args:
        extras: Additional scoring signals merged into the score payload.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            compute_trust(
                extras={"enabled": True},
            )
        Output:
            0.75
    """
    return trust_score(
        source_class=0.4,
        channel_credibility=channel_credibility(extras.get("channel_subscribers")),
        citation_traceability=0.3,
        ai_slop_penalty=0.0,
        corroboration_score=0.3,
    )


def compute_trend(z_velocity: float, z_engagement: float, cross_rep: float, age: float) -> float:
    """Compute trend from normalized metrics.

    Args:
        z_velocity: Numeric score, threshold, prior, or confidence value.
        z_engagement: Numeric score, threshold, prior, or confidence value.
        cross_rep: Numeric score, threshold, prior, or confidence value.
        age: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            compute_trend(
                z_velocity=0.75,
                z_engagement=0.75,
                cross_rep=0.75,
                age=0.75,
            )
        Output:
            0.75
    """
    return trend_score(
        z_view_velocity=z_velocity,
        z_engagement_ratio=z_engagement,
        z_cross_channel_repetition=cross_rep,
        age_days=age,
    )


def compute_opportunity(engagement: float, cross_rep: float, age: float) -> float:
    """Compute opportunity from normalized metrics.

    Args:
        engagement: Numeric score, threshold, prior, or confidence value.
        cross_rep: Numeric score, threshold, prior, or confidence value.
        age: Numeric score, threshold, prior, or confidence value.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            compute_opportunity(
                engagement=0.75,
                cross_rep=0.75,
                age=0.75,
            )
        Output:
            0.75
    """
    return opportunity_score(
        market_gap=max(0.0, 1.0 - cross_rep),
        monetization_proxy=min(1.0, engagement * 20),
        feasibility=0.5,
        novelty=max(0.0, 1.0 - age / 180.0),
    )


def build_features(velocity: float, engagement: float, age: float, subscribers: int | None) -> dict:
    """Build build features in the shape consumed by the next project step.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        velocity: Numeric score, threshold, prior, or confidence value.
        engagement: Numeric score, threshold, prior, or confidence value.
        age: Numeric score, threshold, prior, or confidence value.
        subscribers: Subscriber count used in source credibility scoring.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            build_features(
                velocity=0.75,
                engagement=0.75,
                age=0.75,
                subscribers="AI safety",
            )
        Output:
            {"enabled": True}
    """
    return {
        "view_velocity": velocity,
        "engagement_ratio": engagement,
        "age_days": age,
        "subscriber_count": float(subscribers or 0),
    }


def _metric_values(metrics: EngagementMetrics | None) -> tuple[float, float, float]:
    """Document the metric values rule at the boundary where callers use it.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        metrics: Metric dictionary used by scoring calculations.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _metric_values(
                metrics="AI safety",
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
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
    """Document the score one rule at the boundary where callers use it.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        item: Single source item, database row, or registry entry being transformed.
        metrics: Metric dictionary used by scoring calculations.
        z_velocity: Numeric score, threshold, prior, or confidence value.
        z_engagement: Numeric score, threshold, prior, or confidence value.
        weights: Scoring weights used to combine component scores.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            score_one(
                item={"title": "Example", "url": "https://youtu.be/demo"},
                metrics="AI safety",
                z_velocity=0.75,
                z_engagement=0.75,
                weights="AI safety",
            )
        Output:
            {"enabled": True}
    """
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
    """Compute trust/trend/opportunity/overall per item and rank descending.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.
        weights: Scoring weights used to combine component scores.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            score_items(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                engagement_metrics={"views": 1200, "likes": 80},
                weights="AI safety",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Technology wrapper for computing full scores for a batch of items.

    Examples:
        Input:
            ScoringComputeTech
        Output:
            ScoringComputeTech
    """

    name: ClassVar[str] = "scoring.compute"
    enabled_config_key: ClassVar[str] = "scoring_compute"

    async def _execute(self, input_data: object) -> list:
        """Run this component and return the project-shaped output expected by its service.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            input_data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    input_data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        items = input_data.get("items", []) if isinstance(input_data, dict) else []
        metrics = input_data.get("engagement_metrics", []) if isinstance(input_data, dict) else []
        weights = input_data.get("weights", {}) if isinstance(input_data, dict) else None
        return score_items(items, metrics, weights)
