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
    """Document the comment to row rule at the boundary where callers use it.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        source_url: Stable source identifier or URL used to join records across stages and exports.
        source_title: Human-readable source title stored with extracted claims or citations.
        comment: Single comment record being flattened for export.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _comment_to_row(
                source_url="https://youtu.be/abc123",
                source_title="Example video",
                comment="AI safety",
            )
        Output:
            {"enabled": True}
    """
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
    """Build tabular rows for CSV or HTML output.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _rows_for_item(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    source_url = item.get("url", "")
    source_title = item.get("title", "")
    comments = item.get("source_comments") or []
    return [_comment_to_row(source_url, source_title, c) for c in comments]


def build_comments_rows(items: list[dict]) -> list[dict[str, object]]:
    """Flatten source_comments from all items into CSV-ready row dicts.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            build_comments_rows(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    rows: list[dict[str, object]] = []
    for item in items:
        rows.extend(_rows_for_item(item))
    return rows


def write_comments_csv(rows: list[dict[str, object]], path: Path) -> Path:
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
            write_comments_csv(
                rows=[[1.0, 2.0], [3.0, 4.0]],
                path=Path("report.html"),
            )
        Output:
            None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMMENTS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
