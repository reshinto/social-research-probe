"""Scoring services."""

from __future__ import annotations

from social_research_probe.technologies.scoring import (
    _metric_values,
    age_days,
    build_features,
    channel_credibility,
    compute_opportunity,
    compute_trend,
    compute_trust,
    normalize_item,
    normalize_with_metrics,
    score_items,
    score_one,
    zscores,
)
from social_research_probe.technologies.scoring.combine import DEFAULT_WEIGHTS
from social_research_probe.utils.purposes.merge import MergedPurpose

__all__ = [
    "DEFAULT_WEIGHTS",
    "_metric_values",
    "age_days",
    "build_features",
    "channel_credibility",
    "compute_opportunity",
    "compute_trend",
    "compute_trust",
    "normalize_item",
    "normalize_with_metrics",
    "resolve_scoring_weights",
    "score_items",
    "score_one",
    "zscores",
]


def resolve_scoring_weights(merged: MergedPurpose) -> dict[str, float]:
    """Merge spec §6 defaults with config-wide overrides, then purpose-specific overrides.

    Precedence (later wins): DEFAULT_WEIGHTS → [scoring.weights] in config.toml → merged
    purpose ``scoring_overrides``. Only keys ``trust``, ``trend``, and ``opportunity`` are
    recognised; unknown keys are silently ignored.

    Args:
        merged: Merged purpose or report data produced by earlier normalization.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            resolve_scoring_weights(
                merged="AI safety",
            )
        Output:
            {"enabled": True}
    """
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    resolved: dict[str, float] = dict(DEFAULT_WEIGHTS)
    config_weights = cfg.raw.get("scoring", {}).get("weights", {})
    for key in ("trust", "trend", "opportunity"):
        if key in config_weights:
            resolved[key] = float(config_weights[key])
        if key in merged.scoring_overrides:
            resolved[key] = float(merged.scoring_overrides[key])
    return resolved
