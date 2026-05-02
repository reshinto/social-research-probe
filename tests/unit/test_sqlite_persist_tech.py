"""Tests for SQLitePersistTech end-of-run writer."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from social_research_probe.technologies.persistence.sqlite import SQLitePersistTech


def _minimal_report(**overrides) -> dict:
    report = {
        "topic": "AI safety",
        "platform": "youtube",
        "purpose_set": ["research"],
        "items_top_n": [],
        "warnings": [],
        "export_paths": {},
    }
    report.update(overrides)
    return report


def _item(
    *,
    video_id: str = "vid1",
    title: str = "Test Video",
    channel: str = "Test Channel",
    url: str | None = None,
    transcript: str | None = "hello world",
    transcript_status: str = "available",
    comments: list[dict] | None = None,
    surrogate: dict | None = None,
    scores: dict | None = None,
) -> dict:
    item: dict = {
        "title": title,
        "channel": channel,
        "url": url or f"https://youtube.com/watch?v={video_id}",
        "transcript": transcript,
        "transcript_status": transcript_status,
        "source_comments": comments or [],
        "text_surrogate": surrogate
        or {
            "source_id": video_id,
            "platform": "youtube",
            "primary_text": transcript or "",
            "primary_text_source": "transcript",
            "evidence_layers": ["transcript"],
            "evidence_tier": "metadata_transcript",
            "confidence_penalties": [],
            "warnings": [],
            "char_count": len(transcript) if transcript else 0,
            "description": "A description",
        },
        "scores": scores or {"trust": 0.8, "trend": 0.5, "opportunity": 0.3, "overall": 0.6},
        "features": {
            "view_velocity": 1.0,
            "engagement_ratio": 0.05,
            "age_days": 10.0,
            "subscriber_count": 1000.0,
        },
        "evidence_tier": "metadata_transcript",
        "comments_status": "available",
    }
    return item


def _comment(*, comment_id: str = "c1", text: str = "Great video!", author: str = "User1") -> dict:
    return {
        "comment_id": comment_id,
        "author": author,
        "text": text,
        "like_count": 5,
        "published_at": "2026-01-01T00:00:00",
        "source_id": "vid1",
        "platform": "youtube",
    }


async def _run(tmp_path: Path, data: dict) -> dict | None:
    tech = SQLitePersistTech()
    return await tech._execute(data)


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.mark.asyncio
async def test_execute_writes_run_and_returns_pk(db_path: Path) -> None:
    report = _minimal_report()
    result = await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    assert result is not None
    assert result["run_pk"] >= 1
    assert result["run_id"]
    assert result["db_path"] == str(db_path)
    assert db_path.exists()


@pytest.mark.asyncio
async def test_execute_writes_source_snapshot_for_each_item(db_path: Path) -> None:
    report = _minimal_report(items_top_n=[_item(video_id="a"), _item(video_id="b")])
    result = await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    assert result is not None
    assert result["persisted_source_count"] == 2
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert rows == 2
    snaps = conn.execute("SELECT COUNT(*) FROM source_snapshots").fetchone()[0]
    assert snaps == 2
    conn.close()


@pytest.mark.asyncio
async def test_execute_persists_comments(db_path: Path) -> None:
    item = _item(comments=[_comment(comment_id="c1"), _comment(comment_id="c2")])
    report = _minimal_report(items_top_n=[item])
    result = await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    assert result is not None
    assert result["persisted_comment_count"] == 2
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT text FROM comments").fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "Great video!"
    conn.close()


@pytest.mark.asyncio
async def test_execute_persists_transcript_metadata(db_path: Path) -> None:
    report = _minimal_report(
        items_top_n=[_item(transcript="hello world", transcript_status="available")]
    )
    await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT status, char_count, text_digest FROM transcripts").fetchone()
    assert row is not None
    assert row[0] == "available"
    assert row[1] is not None
    conn.close()


@pytest.mark.asyncio
async def test_execute_persists_text_surrogate(db_path: Path) -> None:
    report = _minimal_report(items_top_n=[_item(video_id="v1")])
    await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT primary_text_source, evidence_tier FROM text_surrogates").fetchone()
    assert row is not None
    assert row[0] == "transcript"
    assert row[1] == "metadata_transcript"
    conn.close()


@pytest.mark.asyncio
async def test_execute_persists_warnings(db_path: Path) -> None:
    report = _minimal_report(warnings=["something went wrong", "another issue"])
    await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM warnings").fetchone()[0]
    assert count == 2
    conn.close()


@pytest.mark.asyncio
async def test_execute_persists_artifacts(db_path: Path) -> None:
    report = _minimal_report(
        html_report_path="file:///tmp/reports/run-001.html",
        export_paths={"sources_csv": "/tmp/reports/run-001-sources.csv"},
    )
    await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    assert count >= 1
    conn.close()


@pytest.mark.asyncio
async def test_execute_persist_transcript_text_false_nulls_text(db_path: Path) -> None:
    report = _minimal_report(items_top_n=[_item(transcript="full text here")])
    await _run(
        db_path,
        {"report": report, "db_path": db_path, "config": {}, "persist_transcript_text": False},
    )
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT text, text_digest FROM transcripts").fetchone()
    assert row is not None
    assert row[0] is None
    assert row[1] is not None  # digest still stored
    conn.close()


@pytest.mark.asyncio
async def test_execute_persist_comment_text_false_nulls_text(db_path: Path) -> None:
    item = _item(comments=[_comment(comment_id="c1", text="some comment text")])
    report = _minimal_report(items_top_n=[item])
    await _run(
        db_path, {"report": report, "db_path": db_path, "config": {}, "persist_comment_text": False}
    )
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT text, text_digest FROM comments").fetchone()
    assert row is not None
    assert row[0] is None
    assert row[1] is not None  # digest still stored
    conn.close()


@pytest.mark.asyncio
async def test_execute_missing_source_id_falls_back_to_hash(db_path: Path) -> None:
    item = _item(video_id="v1")
    item["text_surrogate"] = {}  # no source_id
    report = _minimal_report(items_top_n=[item])
    result = await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    assert result is not None
    assert result["persisted_source_count"] == 1
    conn = sqlite3.connect(str(db_path))
    ext_id = conn.execute("SELECT external_id FROM sources").fetchone()[0]
    assert ext_id.startswith("url-")
    conn.close()


@pytest.mark.asyncio
async def test_execute_sqlite_error_is_isolated_non_fatal(tmp_path: Path) -> None:
    tech = SQLitePersistTech()
    db_path = tmp_path / "error.db"
    report = _minimal_report()

    with patch(
        "social_research_probe.technologies.persistence.sqlite.open_connection",
        side_effect=sqlite3.OperationalError("disk full"),
    ):
        result = await tech.execute({"report": report, "db_path": db_path, "config": {}})

    assert result is None


@pytest.mark.asyncio
async def test_execute_run_id_derived_from_file_uri(db_path: Path) -> None:
    report = _minimal_report(html_report_path="file:///tmp/reports/my-run-2026.html")
    result = await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    assert result is not None
    assert result["run_id"] == "my-run-2026"


@pytest.mark.asyncio
async def test_execute_config_snapshot_persists_database_scoring_platforms(db_path: Path) -> None:
    config = {
        "database": {"enabled": True, "path": ""},
        "scoring": {"weights": {"trust": 0.5}},
        "platforms": {"youtube": {"max_items": 20, "comments": {"enabled": True}}},
    }
    report = _minimal_report()
    await _run(db_path, {"report": report, "db_path": db_path, "config": config})
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT config_snapshot_json FROM research_runs").fetchone()
    assert row is not None
    import json

    snap = json.loads(row[0])
    assert "database" in snap
    assert "scoring" in snap
    assert "platforms" in snap
    conn.close()


@pytest.mark.asyncio
async def test_execute_warning_count_reflects_warnings(db_path: Path) -> None:
    report = _minimal_report(warnings=["w1", "w2", "w3"])
    await _run(db_path, {"report": report, "db_path": db_path, "config": {}})
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT warning_count, exit_status FROM research_runs").fetchone()
    assert row[0] == 3
    assert row[1] == "partial"
    conn.close()
