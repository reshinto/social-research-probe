"""Sources CSV builder: converts ScoredItems to a flat CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

SOURCES_COLUMNS = [
    "rank",
    "title",
    "channel",
    "url",
    "source_class",
    "trust",
    "trend",
    "opportunity",
    "overall",
    "evidence_tier",
    "transcript_status",
    "comments_status",
    "corroboration_verdict",
    "one_line_takeaway",
]


def _extract_scores(item: dict) -> dict[str, object]:
    """Extract extract scores from the provider or service payload.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _extract_scores(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            {"enabled": True}
    """
    scores = item.get("scores") or {}
    return {
        "trust": scores.get("trust", ""),
        "trend": scores.get("trend", ""),
        "opportunity": scores.get("opportunity", ""),
        "overall": scores.get("overall", ""),
    }


def _item_to_row(rank: int, item: dict) -> dict[str, object]:
    """Document the item to row rule at the boundary where callers use it.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        rank: Count, database id, index, or limit that bounds the work being performed.
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _item_to_row(
                rank=3,
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            {"enabled": True}
    """
    score_fields = _extract_scores(item)
    return {
        "rank": rank,
        "title": item.get("title", ""),
        "channel": item.get("channel", ""),
        "url": item.get("url", ""),
        "source_class": item.get("source_class", ""),
        "trust": score_fields["trust"],
        "trend": score_fields["trend"],
        "opportunity": score_fields["opportunity"],
        "overall": score_fields["overall"],
        "evidence_tier": item.get("evidence_tier", ""),
        "transcript_status": item.get("transcript_status", ""),
        "comments_status": item.get("comments_status", ""),
        "corroboration_verdict": item.get("corroboration_verdict", ""),
        "one_line_takeaway": item.get("one_line_takeaway", ""),
    }


def build_sources_rows(items: list[dict]) -> list[dict[str, object]]:
    """Convert ScoredItems to flat CSV-ready row dicts, one per item.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            build_sources_rows(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    return [_item_to_row(rank, item) for rank, item in enumerate(items, start=1)]


def write_sources_csv(rows: list[dict[str, object]], path: Path) -> Path:
    """Write rows to CSV at path. Always writes headers. Returns path.

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
            write_sources_csv(
                rows=[[1.0, 2.0], [3.0, 4.0]],
                path=Path("report.html"),
            )
        Output:
            None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SOURCES_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
