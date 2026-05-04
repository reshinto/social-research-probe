"""Run summary JSON builder: machine-readable metadata for a completed research run."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from social_research_probe.utils.io.io import write_json


def _item_counts(items: list[dict]) -> dict[str, int]:
    """Document the item counts rule at the boundary where callers use it.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _item_counts(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    total = len(items)
    enriched = sum(
        1
        for it in items
        if isinstance(it, dict)
        and it.get("transcript_status") not in (None, "not_attempted", "disabled")
    )
    return {"fetched": total, "enriched": enriched}


def _evidence_tiers(items: list[dict]) -> dict[str, int]:
    """Document the evidence tiers rule at the boundary where callers use it.

    Extraction, review, corroboration, and reporting all need the same claim shape.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _evidence_tiers(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    return dict(Counter(it.get("evidence_tier", "unknown") for it in items if isinstance(it, dict)))


def _corroboration_summary(items: list[dict]) -> dict[str, int]:
    """Document the corroboration summary rule at the boundary where callers use it.

    Downstream stages can read the same fields regardless of which source text was available.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _corroboration_summary(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    return dict(
        Counter(
            it.get("corroboration_verdict", "unknown")
            for it in items
            if isinstance(it, dict) and "corroboration_verdict" in it
        )
    )


def _claims_summary(items: list[dict]) -> dict:
    """Document the claims summary rule at the boundary where callers use it.

    The report pipeline needs a predictable text payload even when transcripts or summaries are
    missing.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _claims_summary(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    all_claims: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            all_claims.extend(
                c for c in (item.get("extracted_claims") or []) if isinstance(c, dict)
            )
    by_type: dict[str, int] = dict(Counter(c.get("claim_type", "unknown") for c in all_claims))
    by_method: dict[str, int] = dict(
        Counter(c.get("extraction_method", "unknown") for c in all_claims)
    )
    return {
        "claims_extracted": len(all_claims),
        "claims_by_type": by_type,
        "claims_by_extraction_method": by_method,
        "claims_needing_review": sum(1 for c in all_claims if c.get("needs_review")),
        "claims_needing_corroboration": sum(1 for c in all_claims if c.get("needs_corroboration")),
        "corroborated_claims": sum(
            1 for c in all_claims if c.get("corroboration_status") not in (None, "pending")
        ),
    }


def _top_narrative_items(clusters: list[dict], score_key: str) -> list[dict]:
    """Return top 3 cluster dicts sorted by score_key descending."""
    valid = [c for c in clusters if isinstance(c, dict)]
    ranked = sorted(valid, key=lambda c: c.get(score_key, 0.0), reverse=True)
    return [
        {
            "narrative_id": c.get("narrative_id", ""),
            "title": c.get("title", ""),
            score_key: c.get(score_key, 0.0),
        }
        for c in ranked[:3]
    ]


def _narratives_summary(report: dict) -> dict:
    """Build narrative clustering summary for run_summary JSON."""
    clusters = report.get("narratives") or []
    if not clusters:
        return {
            "cluster_count": 0,
            "by_type": {},
            "avg_confidence": 0.0,
            "total_claims_clustered": 0,
            "top_opportunities": [],
            "top_risks": [],
        }
    valid = [c for c in clusters if isinstance(c, dict)]
    by_type: dict[str, int] = dict(Counter(c.get("cluster_type", "mixed") for c in valid))
    confidences = [c.get("confidence", 0.0) for c in valid]
    avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    total_claims = sum(c.get("claim_count", 0) for c in valid)
    return {
        "cluster_count": len(clusters),
        "by_type": by_type,
        "avg_confidence": avg_confidence,
        "total_claims_clustered": total_claims,
        "top_opportunities": _top_narrative_items(clusters, "opportunity_score"),
        "top_risks": _top_narrative_items(clusters, "risk_score"),
    }


def _config_snapshot(config: dict) -> dict:
    """Build the small payload that carries youtube through this workflow.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        config: Configuration or context values that control this run.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _config_snapshot(
                config={"enabled": True},
            )
        Output:
            {"enabled": True}
    """
    platform_keys = {
        k: config[k]
        for k in ("max_items", "enrich_top_n", "recency_days", "comments", "export")
        if k in config
    }
    return {"youtube": platform_keys} if platform_keys else {}


def build_run_summary(report: dict, config: dict, artifact_paths: dict[str, str]) -> dict:
    """Build machine-readable run summary dict.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        config: Configuration or context values that control this run.
        artifact_paths: Filesystem location used to read, write, or resolve project data.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            build_run_summary(
                report={"topic": "AI safety", "items_top_n": []},
                config={"enabled": True},
                artifact_paths=Path("report.html"),
            )
        Output:
            {"enabled": True}
    """
    items = report.get("items_top_n") or []
    claims = _claims_summary(items)
    return {
        "topic": report.get("topic", ""),
        "platform": report.get("platform", ""),
        "timestamp": datetime.now(UTC).isoformat(),
        "purpose_set": list(report.get("purpose_set") or []),
        "item_count": _item_counts(items),
        "evidence_tiers": _evidence_tiers(items),
        "corroboration_summary": _corroboration_summary(items),
        "claims_extracted": claims["claims_extracted"],
        "claims_by_type": claims["claims_by_type"],
        "claims_by_extraction_method": claims["claims_by_extraction_method"],
        "claims_needing_review": claims["claims_needing_review"],
        "claims_needing_corroboration": claims["claims_needing_corroboration"],
        "corroborated_claims": claims["corroborated_claims"],
        "narratives_summary": _narratives_summary(report),
        "stage_timings": list(report.get("stage_timings") or []),
        "config_snapshot": _config_snapshot(config),
        "artifact_paths": dict(artifact_paths),
        "warnings": list(report.get("warnings") or []),
    }


def write_run_summary(summary: dict, path: Path) -> Path:
    """Write run summary JSON to path atomically. Returns path.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        summary: Run summary dictionary being exported.
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            write_run_summary(
                summary={"enabled": True},
                path=Path("report.html"),
            )
        Output:
            None
    """
    write_json(path, summary)
    return path
