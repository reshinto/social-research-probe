"""Tests for Phase 3 comments CSV builder."""

from __future__ import annotations

import csv
from pathlib import Path

from social_research_probe.technologies.report_render.export.comments_csv import (
    COMMENTS_COLUMNS,
    build_comments_rows,
    write_comments_csv,
)


def _make_comment(n: int = 1) -> dict:
    return {
        "comment_id": f"cid{n}",
        "author": f"Author{n}",
        "text": f"Comment text {n}",
        "like_count": n * 10,
        "published_at": f"2026-01-0{n}T00:00:00Z",
    }


def _make_item(
    title: str = "Title", url: str = "https://example.com", comments: list | None = None
) -> dict:
    item: dict = {"title": title, "url": url}
    if comments is not None:
        item["source_comments"] = comments
    return item


def test_build_rows_flattens_comments():
    items = [
        _make_item("A", "https://a.com", [_make_comment(1), _make_comment(2), _make_comment(3)]),
        _make_item("B", "https://b.com", [_make_comment(4), _make_comment(5), _make_comment(6)]),
    ]
    rows = build_comments_rows(items)
    assert len(rows) == 6


def test_build_rows_includes_source_url():
    items = [_make_item("T", "https://my.url/v?v=abc", [_make_comment()])]
    rows = build_comments_rows(items)
    assert rows[0]["source_url"] == "https://my.url/v?v=abc"


def test_build_rows_includes_source_title():
    items = [_make_item("My Title", "https://x.com", [_make_comment()])]
    rows = build_comments_rows(items)
    assert rows[0]["source_title"] == "My Title"


def test_build_rows_no_source_comments_key():
    items = [_make_item("T", "https://x.com")]  # no source_comments key
    assert build_comments_rows(items) == []


def test_build_rows_empty_source_comments():
    items = [_make_item("T", "https://x.com", [])]
    assert build_comments_rows(items) == []


def test_build_rows_mixed():
    items = [
        _make_item("A", "https://a.com", [_make_comment(1), _make_comment(2)]),
        _make_item("B", "https://b.com"),  # no comments
    ]
    rows = build_comments_rows(items)
    assert len(rows) == 2
    assert all(r["source_url"] == "https://a.com" for r in rows)


def test_build_rows_malformed_comment():
    items = [_make_item("T", "https://x.com", ["not-a-dict", None, 42])]
    rows = build_comments_rows(items)
    assert len(rows) == 3
    for row in rows:
        assert set(row.keys()) == set(COMMENTS_COLUMNS)
        assert row["comment_id"] == ""


def test_write_csv_creates_file(tmp_path: Path):
    rows = build_comments_rows([_make_item("T", "https://x.com", [_make_comment()])])
    out = tmp_path / "comments.csv"
    write_comments_csv(rows, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    for col in COMMENTS_COLUMNS:
        assert col in content


def test_write_csv_headers_only_when_empty(tmp_path: Path):
    out = tmp_path / "comments.csv"
    write_comments_csv([], out)
    assert out.exists()
    with out.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COMMENTS_COLUMNS
        assert list(reader) == []


def test_write_csv_unicode_and_commas_roundtrip(tmp_path: Path):
    comment = {
        "comment_id": "c1",
        "author": "日本語ユーザー",
        "text": "Great, amazing, wow",
        "like_count": 5,
        "published_at": "2026-01-01T00:00:00Z",
    }
    items = [_make_item("日本語タイトル", "https://x.com", [comment])]
    rows = build_comments_rows(items)
    out = tmp_path / "comments.csv"
    write_comments_csv(rows, out)
    with out.open(encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert reader[0]["author"] == "日本語ユーザー"
    assert reader[0]["text"] == "Great, amazing, wow"
    assert reader[0]["source_title"] == "日本語タイトル"


def test_build_rows_does_not_mutate_items():
    comment = _make_comment()
    item = _make_item("T", "https://x.com", [comment])
    original_keys = set(item.keys())
    build_comments_rows([item])
    assert set(item.keys()) == original_keys
    assert item["source_comments"] == [comment]
