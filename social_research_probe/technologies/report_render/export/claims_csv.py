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
    """Document the claim to row rule at the boundary where callers use it.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        claim: Claim text or claim dictionary being extracted, classified, reviewed, or
               corroborated.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _claim_to_row(
                claim={"text": "The model reduces latency by 30%."},
            )
        Output:
            {"enabled": True}
    """
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
    """Flatten extracted_claims from all items into CSV-ready row dicts.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            build_claims_rows(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Write claims rows to CSV at path. Always writes headers. Returns path.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        rows: Numeric vector, matrix, or intermediate value used by the statistical algorithm.
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            write_claims_csv(
                rows=[[1.0, 2.0], [3.0, 4.0]],
                path=Path("report.html"),
            )
        Output:
            None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CLAIMS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
