"""Narrative-level comparison between two runs."""

from __future__ import annotations

import json

from social_research_probe.utils.comparison.types import NarrativeChange

_JACCARD_THRESHOLD = 0.5


def _parse_entities(entities_json: str | None) -> set[str]:
    if not entities_json:
        return set()
    try:
        parsed = json.loads(entities_json)
    except (json.JSONDecodeError, TypeError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {str(e).lower() for e in parsed if e}


def entity_jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _strength_signal(
    confidence_change: float, claim_count_change: int
) -> str:
    if claim_count_change > 0 or confidence_change > 0.1:
        return "strengthened"
    if claim_count_change < 0 or confidence_change < -0.1:
        return "weakened"
    return "stable"


def compare_narratives(
    baseline: list[dict], target: list[dict]
) -> list[NarrativeChange]:
    """Compute narrative deltas between baseline and target runs."""
    baseline_by_id = {n["narrative_id"]: n for n in baseline}
    target_by_id = {n["narrative_id"]: n for n in target}

    matched_baseline_ids: set[str] = set()
    changes: list[NarrativeChange] = []

    for t in target:
        tid = t["narrative_id"]
        b = baseline_by_id.get(tid)
        match_method = ""
        matched_id = ""

        if b is not None:
            match_method = "exact_id"
            matched_id = tid
            matched_baseline_ids.add(tid)
        else:
            b, matched_id = _fuzzy_match(t, baseline, matched_baseline_ids)
            if b is not None:
                match_method = "entity_overlap"
                matched_baseline_ids.add(matched_id)

        if b is not None:
            changes.append(_build_repeated(t, b, match_method, matched_id))
        else:
            changes.append(_build_new(t))

    for n in baseline:
        nid = n["narrative_id"]
        if nid not in matched_baseline_ids:
            changes.append(_build_disappeared(n))

    return _sort_changes(changes)


def _fuzzy_match(
    target_narr: dict,
    baseline: list[dict],
    already_matched: set[str],
) -> tuple[dict | None, str]:
    t_type = target_narr.get("cluster_type", "")
    t_entities = _parse_entities(target_narr.get("entities_json"))
    if not t_entities:
        return None, ""

    best: dict | None = None
    best_id = ""
    best_score = 0.0

    for b in baseline:
        bid = b["narrative_id"]
        if bid in already_matched:
            continue
        if b.get("cluster_type", "") != t_type:
            continue
        b_entities = _parse_entities(b.get("entities_json"))
        score = entity_jaccard(t_entities, b_entities)
        if score >= _JACCARD_THRESHOLD and score > best_score:
            best = b
            best_id = bid
            best_score = score

    return best, best_id


def _build_repeated(
    t: dict, b: dict, match_method: str, matched_id: str
) -> NarrativeChange:
    conf_change = (t.get("confidence") or 0.0) - (b.get("confidence") or 0.0)
    opp_change = (t.get("opportunity_score") or 0.0) - (b.get("opportunity_score") or 0.0)
    risk_change = (t.get("risk_score") or 0.0) - (b.get("risk_score") or 0.0)
    claim_change = (t.get("claim_count") or 0) - (b.get("claim_count") or 0)
    source_change = (t.get("source_count") or 0) - (b.get("source_count") or 0)

    return NarrativeChange(
        narrative_id=t["narrative_id"],
        title=t.get("title") or "",
        cluster_type=t.get("cluster_type") or "",
        status="repeated",
        match_method=match_method,
        matched_id=matched_id,
        confidence_change=round(conf_change, 4),
        opportunity_change=round(opp_change, 4),
        risk_change=round(risk_change, 4),
        claim_count_change=claim_change,
        source_count_change=source_change,
        strength_signal=_strength_signal(conf_change, claim_change),
    )


def _build_new(t: dict) -> NarrativeChange:
    return NarrativeChange(
        narrative_id=t["narrative_id"],
        title=t.get("title") or "",
        cluster_type=t.get("cluster_type") or "",
        status="new",
        match_method="",
        matched_id="",
        confidence_change=0.0,
        opportunity_change=0.0,
        risk_change=0.0,
        claim_count_change=0,
        source_count_change=0,
        strength_signal="",
    )


def _build_disappeared(b: dict) -> NarrativeChange:
    return NarrativeChange(
        narrative_id=b["narrative_id"],
        title=b.get("title") or "",
        cluster_type=b.get("cluster_type") or "",
        status="disappeared",
        match_method="",
        matched_id="",
        confidence_change=0.0,
        opportunity_change=0.0,
        risk_change=0.0,
        claim_count_change=0,
        source_count_change=0,
        strength_signal="",
    )


def _sort_changes(changes: list[NarrativeChange]) -> list[NarrativeChange]:
    order = {"new": 0, "repeated": 1, "disappeared": 2}
    return sorted(changes, key=lambda c: (order.get(c["status"], 9), c["narrative_id"]))
