"""Export comparison results to CSV and JSON artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from social_research_probe.utils.comparison.types import ComparisonResult

SOURCE_COLUMNS = [
    "source_id", "platform", "external_id", "url", "title", "status",
    "trust_change", "trend_change", "opportunity_change", "overall_change",
    "evidence_tier_baseline", "evidence_tier_target",
]

CLAIM_COLUMNS = [
    "claim_id", "claim_text", "claim_type", "source_url", "status",
    "confidence_change", "corroboration_changed",
    "baseline_corroboration", "target_corroboration",
]

NARRATIVE_COLUMNS = [
    "narrative_id", "title", "cluster_type", "status", "match_method",
    "matched_id", "confidence_change", "opportunity_change", "risk_change",
    "claim_count_change", "source_count_change", "strength_signal",
]


def _build_source_rows(result: ComparisonResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for s in result["source_changes"]:
        scores = s["score_changes"]
        rows.append({
            "source_id": s["source_id"],
            "platform": s["platform"],
            "external_id": s["external_id"],
            "url": s["url"],
            "title": s["title"],
            "status": s["status"],
            "trust_change": scores.get("trust", ""),
            "trend_change": scores.get("trend", ""),
            "opportunity_change": scores.get("opportunity", ""),
            "overall_change": scores.get("overall", ""),
            "evidence_tier_baseline": s["evidence_tier_baseline"],
            "evidence_tier_target": s["evidence_tier_target"],
        })
    return rows


def _build_claim_rows(result: ComparisonResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for c in result["claim_changes"]:
        rows.append({
            "claim_id": c["claim_id"],
            "claim_text": c["claim_text"],
            "claim_type": c["claim_type"],
            "source_url": c["source_url"],
            "status": c["status"],
            "confidence_change": c["confidence_change"],
            "corroboration_changed": c["corroboration_changed"],
            "baseline_corroboration": c["baseline_corroboration"],
            "target_corroboration": c["target_corroboration"],
        })
    return rows


def _build_narrative_rows(result: ComparisonResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for n in result["narrative_changes"]:
        rows.append({
            "narrative_id": n["narrative_id"],
            "title": n["title"],
            "cluster_type": n["cluster_type"],
            "status": n["status"],
            "match_method": n["match_method"],
            "matched_id": n["matched_id"],
            "confidence_change": n["confidence_change"],
            "opportunity_change": n["opportunity_change"],
            "risk_change": n["risk_change"],
            "claim_count_change": n["claim_count_change"],
            "source_count_change": n["source_count_change"],
            "strength_signal": n["strength_signal"],
        })
    return rows


def _write_csv(
    path: Path, columns: list[str], rows: list[dict[str, object]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_comparison_artifacts(
    result: ComparisonResult, output_dir: Path
) -> dict[str, str]:
    """Write all comparison export files. Returns {artifact_name: path}."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"compare-{result['baseline']['run_pk']}-vs-{result['target']['run_pk']}"

    sources_path = output_dir / f"{stem}-sources.csv"
    claims_path = output_dir / f"{stem}-claims.csv"
    narratives_path = output_dir / f"{stem}-narratives.csv"
    summary_path = output_dir / f"{stem}-summary.json"

    _write_csv(sources_path, SOURCE_COLUMNS, _build_source_rows(result))
    _write_csv(claims_path, CLAIM_COLUMNS, _build_claim_rows(result))
    _write_csv(narratives_path, NARRATIVE_COLUMNS, _build_narrative_rows(result))

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    return {
        "sources_csv": str(sources_path),
        "claims_csv": str(claims_path),
        "narratives_csv": str(narratives_path),
        "summary_json": str(summary_path),
    }
