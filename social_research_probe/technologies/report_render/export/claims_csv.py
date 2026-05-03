"""Claims CSV builder: converts extracted claims to a flat CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

CLAIMS_COLUMNS = [
    "claim_id",
    "source_id",
    "source_url",
    "source_title",
    "claim_text",
    "claim_type",
    "evidence_text",
    "entities",
    "confidence",
    "evidence_layer",
    "evidence_tier",
    "needs_corroboration",
    "corroboration_status",
    "contradiction_status",
    "needs_review",
    "uncertainty",
    "extraction_method",
]


def _claim_to_row(claim: dict) -> dict[str, object]:
    entities = claim.get("entities") or []
    return {
        "claim_id": claim.get("claim_id", ""),
        "source_id": claim.get("source_id", ""),
        "source_url": claim.get("source_url", ""),
        "source_title": claim.get("source_title", ""),
        "claim_text": claim.get("claim_text", ""),
        "claim_type": claim.get("claim_type", ""),
        "evidence_text": claim.get("evidence_text", ""),
        "entities": "; ".join(str(e) for e in entities) if entities else "",
        "confidence": claim.get("confidence", ""),
        "evidence_layer": claim.get("evidence_layer", ""),
        "evidence_tier": claim.get("evidence_tier", ""),
        "needs_corroboration": claim.get("needs_corroboration", ""),
        "corroboration_status": claim.get("corroboration_status", ""),
        "contradiction_status": claim.get("contradiction_status", ""),
        "needs_review": claim.get("needs_review", ""),
        "uncertainty": claim.get("uncertainty", ""),
        "extraction_method": claim.get("extraction_method", ""),
    }


def build_claims_rows(items: list) -> list[dict[str, object]]:
    """Flatten extracted_claims from all items into CSV-ready row dicts."""
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        claims = item.get("extracted_claims") or []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            rows.append(_claim_to_row(claim))
    return rows


def write_claims_csv(rows: list[dict[str, object]], path: Path) -> Path:
    """Write claims rows to CSV at path. Always writes headers. Returns path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CLAIMS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
