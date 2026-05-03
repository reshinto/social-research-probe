"""Trend signal derivation from comparison deltas."""

from __future__ import annotations

from social_research_probe.utils.comparison.types import (
    ClaimChange,
    NarrativeChange,
    TrendSignal,
)

_MAX_SIGNALS = 10


def derive_trends(
    narrative_changes: list[NarrativeChange],
    claim_changes: list[ClaimChange],
) -> list[TrendSignal]:
    """Derive trend signals from narrative and claim deltas."""
    signals: list[TrendSignal] = []

    signals.extend(_emerging_narratives(narrative_changes))
    signals.extend(_rising_risk(narrative_changes))
    signals.extend(_growing_opportunity(narrative_changes))
    signals.extend(_weakening_narratives(narrative_changes))
    signals.extend(_rising_objections(narrative_changes))
    signals.extend(_claim_surge(claim_changes))
    signals.extend(_corroboration_trends(claim_changes))

    signals.sort(key=lambda s: s["score"], reverse=True)
    return signals[:_MAX_SIGNALS]


def _emerging_narratives(changes: list[NarrativeChange]) -> list[TrendSignal]:
    signals: list[TrendSignal] = []
    for n in changes:
        if n["status"] == "new" and n.get("claim_count_change", 0) >= 3:
            signals.append(TrendSignal(
                signal_type="emerging_narrative",
                title=f"Emerging: {n['title']}",
                description=f"New narrative with significant claim backing",
                narrative_id=n["narrative_id"],
                score=0.8,
            ))
    return signals


def _rising_risk(changes: list[NarrativeChange]) -> list[TrendSignal]:
    signals: list[TrendSignal] = []
    for n in changes:
        if n["status"] == "repeated" and n["risk_change"] >= 0.15:
            signals.append(TrendSignal(
                signal_type="rising_risk",
                title=f"Rising risk: {n['title']}",
                description=f"Risk score increased by {n['risk_change']:.2f}",
                narrative_id=n["narrative_id"],
                score=0.7 + min(n["risk_change"], 0.3),
            ))
    return signals


def _growing_opportunity(changes: list[NarrativeChange]) -> list[TrendSignal]:
    signals: list[TrendSignal] = []
    for n in changes:
        if n["status"] == "repeated" and n["opportunity_change"] >= 0.15:
            signals.append(TrendSignal(
                signal_type="growing_opportunity",
                title=f"Growing opportunity: {n['title']}",
                description=f"Opportunity score increased by {n['opportunity_change']:.2f}",
                narrative_id=n["narrative_id"],
                score=0.7 + min(n["opportunity_change"], 0.3),
            ))
    return signals


def _weakening_narratives(changes: list[NarrativeChange]) -> list[TrendSignal]:
    signals: list[TrendSignal] = []
    for n in changes:
        if n["status"] == "repeated" and n["strength_signal"] == "weakened":
            signals.append(TrendSignal(
                signal_type="weakening_narrative",
                title=f"Weakening: {n['title']}",
                description=f"Narrative losing strength",
                narrative_id=n["narrative_id"],
                score=0.6,
            ))
    return signals


def _rising_objections(changes: list[NarrativeChange]) -> list[TrendSignal]:
    signals: list[TrendSignal] = []
    for n in changes:
        if n["cluster_type"] == "objection" and n["status"] in ("new", "repeated"):
            if n["status"] == "new" or n["strength_signal"] == "strengthened":
                signals.append(TrendSignal(
                    signal_type="rising_objections",
                    title=f"Rising objection: {n['title']}",
                    description=f"Objection narrative gaining traction",
                    narrative_id=n["narrative_id"],
                    score=0.75,
                ))
    return signals


def _claim_surge(changes: list[ClaimChange]) -> list[TrendSignal]:
    if not changes:
        return []
    new_count = sum(1 for c in changes if c["status"] == "new")
    repeated_count = sum(1 for c in changes if c["status"] == "repeated")
    baseline_approx = repeated_count + sum(1 for c in changes if c["status"] == "disappeared")
    if baseline_approx > 0 and (repeated_count + new_count) > baseline_approx * 1.5:
        return [TrendSignal(
            signal_type="claim_surge",
            title="Claim volume surge",
            description=f"{new_count} new claims detected (baseline had ~{baseline_approx})",
            narrative_id="",
            score=0.65,
        )]
    return []


def _corroboration_trends(changes: list[ClaimChange]) -> list[TrendSignal]:
    repeated = [c for c in changes if c["status"] == "repeated"]
    if not repeated:
        return []

    improved = sum(1 for c in repeated if c["corroboration_changed"] and
                   _is_better_corroboration(c["baseline_corroboration"], c["target_corroboration"]))
    worsened = sum(1 for c in repeated if c["corroboration_changed"] and
                   _is_worse_corroboration(c["baseline_corroboration"], c["target_corroboration"]))

    signals: list[TrendSignal] = []
    threshold = len(repeated) * 0.3

    if improved > threshold:
        signals.append(TrendSignal(
            signal_type="improving_corroboration",
            title="Improving corroboration",
            description=f"{improved}/{len(repeated)} repeated claims gained better corroboration",
            narrative_id="",
            score=0.6,
        ))
    if worsened > threshold:
        signals.append(TrendSignal(
            signal_type="weakening_corroboration",
            title="Weakening corroboration",
            description=f"{worsened}/{len(repeated)} repeated claims lost corroboration",
            narrative_id="",
            score=0.6,
        ))
    return signals


_CORROBORATION_RANK = {
    "confirmed": 4,
    "supported": 3,
    "pending": 2,
    "contradicted": 1,
    "": 0,
}


def _is_better_corroboration(baseline: str, target: str) -> bool:
    return _CORROBORATION_RANK.get(target, 0) > _CORROBORATION_RANK.get(baseline, 0)


def _is_worse_corroboration(baseline: str, target: str) -> bool:
    return _CORROBORATION_RANK.get(target, 0) < _CORROBORATION_RANK.get(baseline, 0)
