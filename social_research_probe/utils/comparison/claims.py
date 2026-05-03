"""Claim-level comparison between two runs."""

from __future__ import annotations

import hashlib
import re

from social_research_probe.utils.comparison.types import ClaimChange


def normalize_claim_text(text: str) -> str:
    """Normalize and hash claim text for fuzzy matching."""
    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def compare_claims(
    baseline: list[dict], target: list[dict]
) -> list[ClaimChange]:
    """Compute claim deltas between baseline and target runs."""
    baseline_by_id: dict[str, dict] = {}
    baseline_by_hash: dict[str, dict] = {}
    for c in baseline:
        cid = c.get("claim_id", "")
        baseline_by_id[cid] = c
        text = c.get("claim_text") or ""
        if text:
            baseline_by_hash[normalize_claim_text(text)] = c

    matched_baseline_ids: set[str] = set()
    changes: list[ClaimChange] = []

    for t in target:
        tid = t.get("claim_id", "")
        t_text = t.get("claim_text") or ""

        b = baseline_by_id.get(tid)
        match_found = b is not None

        if not match_found and t_text:
            t_hash = normalize_claim_text(t_text)
            b = baseline_by_hash.get(t_hash)
            match_found = b is not None

        if match_found and b is not None:
            bid = b.get("claim_id", "")
            matched_baseline_ids.add(bid)
            b_conf = b.get("confidence") or 0.0
            t_conf = t.get("confidence") or 0.0
            b_corr = b.get("corroboration_status") or ""
            t_corr = t.get("corroboration_status") or ""
            b_review = bool(b.get("needs_review"))
            t_review = bool(t.get("needs_review"))
            changes.append(ClaimChange(
                claim_id=tid,
                claim_text=t_text,
                claim_type=t.get("claim_type") or "",
                source_url=t.get("source_url") or "",
                status="repeated",
                confidence_change=round(t_conf - b_conf, 4),
                corroboration_changed=b_corr != t_corr,
                baseline_corroboration=b_corr,
                target_corroboration=t_corr,
                review_status_changed=b_review != t_review,
            ))
        else:
            changes.append(ClaimChange(
                claim_id=tid,
                claim_text=t_text,
                claim_type=t.get("claim_type") or "",
                source_url=t.get("source_url") or "",
                status="new",
                confidence_change=0.0,
                corroboration_changed=False,
                baseline_corroboration="",
                target_corroboration=t.get("corroboration_status") or "",
                review_status_changed=False,
            ))

    for c in baseline:
        cid = c.get("claim_id", "")
        if cid not in matched_baseline_ids:
            changes.append(ClaimChange(
                claim_id=cid,
                claim_text=c.get("claim_text") or "",
                claim_type=c.get("claim_type") or "",
                source_url=c.get("source_url") or "",
                status="disappeared",
                confidence_change=0.0,
                corroboration_changed=False,
                baseline_corroboration=c.get("corroboration_status") or "",
                target_corroboration="",
                review_status_changed=False,
            ))

    return _sort_changes(changes)


def _sort_changes(changes: list[ClaimChange]) -> list[ClaimChange]:
    order = {"new": 0, "repeated": 1, "disappeared": 2}
    return sorted(changes, key=lambda c: (order.get(c["status"], 9), c["claim_id"]))
