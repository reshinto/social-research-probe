"""Source-level comparison between two runs."""

from __future__ import annotations

import json

from social_research_probe.utils.comparison.types import SourceChange


def _parse_scores(scores_json: str | None) -> dict[str, float]:
    if not scores_json:
        return {}
    try:
        parsed = json.loads(scores_json)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {k: float(v) for k, v in parsed.items() if isinstance(v, (int, float))}


def _process_new_source(sid: str, t: dict) -> SourceChange:
    """Process a new source."""
    return SourceChange(
        source_id=sid,
        platform=t.get("platform", ""),
        external_id=t.get("external_id", ""),
        url=t.get("url", ""),
        title=t.get("title", ""),
        status="new",
        score_changes={},
        evidence_tier_baseline="",
        evidence_tier_target=t.get("evidence_tier", ""),
    )


def _process_repeated_source(sid: str, b: dict, t: dict) -> SourceChange:
    """Process a repeated source."""
    b_scores = _parse_scores(b.get("scores_json"))
    t_scores = _parse_scores(t.get("scores_json"))
    all_keys = set(b_scores) | set(t_scores)
    score_changes = {}
    for k in sorted(all_keys):
        delta = t_scores.get(k, 0.0) - b_scores.get(k, 0.0)
        if delta != 0.0:
            score_changes[k] = round(delta, 4)
    return SourceChange(
        source_id=sid,
        platform=t.get("platform", ""),
        external_id=t.get("external_id", ""),
        url=t.get("url", ""),
        title=t.get("title", ""),
        status="repeated",
        score_changes=score_changes,
        evidence_tier_baseline=b.get("evidence_tier", ""),
        evidence_tier_target=t.get("evidence_tier", ""),
    )


def _process_disappeared_source(sid: str, b: dict) -> SourceChange:
    """Process a disappeared source."""
    return SourceChange(
        source_id=sid,
        platform=b.get("platform", ""),
        external_id=b.get("external_id", ""),
        url=b.get("url", ""),
        title=b.get("title", ""),
        status="disappeared",
        score_changes={},
        evidence_tier_baseline=b.get("evidence_tier", ""),
        evidence_tier_target="",
    )


def compare_sources(baseline: list[dict], target: list[dict]) -> list[SourceChange]:
    """Compute source deltas between baseline and target run snapshots."""
    baseline_by_sid = {s["source_id"]: s for s in baseline}
    target_by_sid = {s["source_id"]: s for s in target}

    baseline_ids = set(baseline_by_sid)
    target_ids = set(target_by_sid)

    new_ids = sorted(target_ids - baseline_ids)
    disappeared_ids = sorted(baseline_ids - target_ids)
    repeated_ids = sorted(baseline_ids & target_ids)

    changes: list[SourceChange] = []

    for sid in new_ids:
        changes.append(_process_new_source(sid, target_by_sid[sid]))

    for sid in repeated_ids:
        changes.append(_process_repeated_source(sid, baseline_by_sid[sid], target_by_sid[sid]))

    for sid in disappeared_ids:
        changes.append(_process_disappeared_source(sid, baseline_by_sid[sid]))

    return changes
