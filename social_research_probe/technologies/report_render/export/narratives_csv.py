"""Narratives CSV builder: converts narrative clusters to a flat CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

NARRATIVES_COLUMNS = [
    "narrative_id",
    "title",
    "cluster_type",
    "claim_count",
    "source_count",
    "confidence",
    "opportunity_score",
    "risk_score",
    "contradiction_count",
    "needs_review_count",
    "entities",
    "keywords",
    "evidence_tiers",
    "corroboration_statuses",
    "representative_claims",
    "source_urls",
    "claim_ids",
    "created_at",
]


def _cluster_to_row(cluster: dict) -> dict[str, object]:
    """Convert a NarrativeCluster dict to a flat CSV row.

    Args:
        cluster: NarrativeCluster dictionary.

    Returns:
        Dict mapping column names to serialized values.
    """
    return {
        "narrative_id": cluster.get("narrative_id", ""),
        "title": cluster.get("title", ""),
        "cluster_type": cluster.get("cluster_type", ""),
        "claim_count": cluster.get("claim_count", 0),
        "source_count": cluster.get("source_count", 0),
        "confidence": cluster.get("confidence", 0.0),
        "opportunity_score": cluster.get("opportunity_score", 0.0),
        "risk_score": cluster.get("risk_score", 0.0),
        "contradiction_count": cluster.get("contradiction_count", 0),
        "needs_review_count": cluster.get("needs_review_count", 0),
        "entities": "; ".join(cluster.get("entities") or []),
        "keywords": "; ".join(cluster.get("keywords") or []),
        "evidence_tiers": "; ".join(cluster.get("evidence_tiers") or []),
        "corroboration_statuses": "; ".join(cluster.get("corroboration_statuses") or []),
        "representative_claims": "; ".join(cluster.get("representative_claims") or []),
        "source_urls": "; ".join(cluster.get("source_urls") or []),
        "claim_ids": "; ".join(cluster.get("claim_ids") or []),
        "created_at": cluster.get("created_at", ""),
    }


def build_narratives_rows(clusters: list[dict]) -> list[dict[str, object]]:
    """Build CSV rows from narrative clusters.

    Args:
        clusters: List of NarrativeCluster dicts from report["narratives"].

    Returns:
        List of flat dicts ready for csv.DictWriter.
    """
    return [_cluster_to_row(c) for c in clusters if isinstance(c, dict)]


def write_narratives_csv(rows: list[dict[str, object]], path: Path) -> Path:
    """Write narrative rows to a CSV file.

    Args:
        rows: Flat row dicts from build_narratives_rows.
        path: Output file path.

    Returns:
        The path written to.
    """
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=NARRATIVES_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path
