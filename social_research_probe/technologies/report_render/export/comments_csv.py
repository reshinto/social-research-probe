"""Comments CSV builder: flattens source_comments across items into a CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

COMMENTS_COLUMNS = [
    "source_url",
    "source_title",
    "comment_id",
    "author",
    "text",
    "like_count",
    "published_at",
]


def _comment_to_row(source_url: str, source_title: str, comment: object) -> dict[str, object]:
    if not isinstance(comment, dict):
        comment = {}
    return {
        "source_url": source_url,
        "source_title": source_title,
        "comment_id": comment.get("comment_id", ""),
        "author": comment.get("author", ""),
        "text": comment.get("text", ""),
        "like_count": comment.get("like_count", ""),
        "published_at": comment.get("published_at", ""),
    }


def _rows_for_item(item: dict) -> list[dict[str, object]]:
    source_url = item.get("url", "")
    source_title = item.get("title", "")
    comments = item.get("source_comments") or []
    return [_comment_to_row(source_url, source_title, c) for c in comments]


def build_comments_rows(items: list[dict]) -> list[dict[str, object]]:
    """Flatten source_comments from all items into CSV-ready row dicts."""
    rows: list[dict[str, object]] = []
    for item in items:
        rows.extend(_rows_for_item(item))
    return rows


def write_comments_csv(rows: list[dict[str, object]], path: Path) -> Path:
    """Write rows to CSV at path. Always writes headers. Returns path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMMENTS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
