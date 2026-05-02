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
    scores = item.get("scores") or {}
    return {
        "trust": scores.get("trust", ""),
        "trend": scores.get("trend", ""),
        "opportunity": scores.get("opportunity", ""),
        "overall": scores.get("overall", ""),
    }


def _item_to_row(rank: int, item: dict) -> dict[str, object]:
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
    """Convert ScoredItems to flat CSV-ready row dicts, one per item."""
    return [_item_to_row(rank, item) for rank, item in enumerate(items, start=1)]


def write_sources_csv(rows: list[dict[str, object]], path: Path) -> Path:
    """Write rows to CSV at path. Always writes headers. Returns path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SOURCES_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
