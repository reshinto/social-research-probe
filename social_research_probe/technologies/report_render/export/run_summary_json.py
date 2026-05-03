"""Run summary JSON builder: machine-readable metadata for a completed research run."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from social_research_probe.utils.io.io import write_json


def _item_counts(items: list[dict]) -> dict[str, int]:
    total = len(items)
    enriched = sum(
        1
        for it in items
        if isinstance(it, dict)
        and it.get("transcript_status") not in (None, "not_attempted", "disabled")
    )
    return {"fetched": total, "enriched": enriched}


def _evidence_tiers(items: list[dict]) -> dict[str, int]:
    return dict(Counter(it.get("evidence_tier", "unknown") for it in items if isinstance(it, dict)))


def _corroboration_summary(items: list[dict]) -> dict[str, int]:
    return dict(
        Counter(
            it.get("corroboration_verdict", "unknown")
            for it in items
            if isinstance(it, dict) and "corroboration_verdict" in it
        )
    )


def _claims_summary(items: list[dict]) -> dict:
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


def _config_snapshot(config: dict) -> dict:
    platform_keys = {
        k: config[k]
        for k in ("max_items", "enrich_top_n", "recency_days", "comments", "export")
        if k in config
    }
    return {"youtube": platform_keys} if platform_keys else {}


def build_run_summary(report: dict, config: dict, artifact_paths: dict[str, str]) -> dict:
    """Build machine-readable run summary dict."""
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
        "stage_timings": list(report.get("stage_timings") or []),
        "config_snapshot": _config_snapshot(config),
        "artifact_paths": dict(artifact_paths),
        "warnings": list(report.get("warnings") or []),
    }


def write_run_summary(summary: dict, path: Path) -> Path:
    """Write run summary JSON to path atomically. Returns path."""
    write_json(path, summary)
    return path
