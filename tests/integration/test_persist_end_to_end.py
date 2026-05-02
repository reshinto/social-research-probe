"""Integration tests for end-to-end SQLite persistence via YouTubePersistStage."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube.pipeline import YouTubePersistStage
from social_research_probe.technologies.persistence.sqlite.connection import open_connection


def _run(coro):
    return asyncio.run(coro)


def _minimal_item(vid_id: str = "vid001") -> dict:
    return {
        "url": f"https://www.youtube.com/watch?v={vid_id}",
        "title": "Test Video",
        "channel": "Test Channel",
        "source_class": "youtube_video",
        "published_at": "2026-01-01T00:00:00Z",
        "scores": {"relevance": 0.8},
        "features": {},
        "text_surrogate": {
            "platform": "youtube",
            "source_id": vid_id,
            "primary_text": "Primary text for the video.",
            "primary_text_source": "transcript",
            "evidence_tier": "tier_1",
            "char_count": 27,
            "evidence_layers": [],
            "confidence_penalties": [],
            "warnings": [],
        },
        "source_comments": [],
        "transcript_status": "available",
        "transcript": "Primary text for the video.",
    }


def _minimal_report(topic: str = "ai agents") -> dict:
    return {
        "topic": topic,
        "platform": "youtube",
        "purpose_set": ["trends"],
        "items_top_n": [_minimal_item()],
        "warnings": [],
        "export_paths": {},
    }


def _state_with_report(report: dict) -> PipelineState:
    state = PipelineState(platform_type="youtube", cmd=None, cache=None, platform_config={})
    state.outputs["report"] = report
    return state


def _cfg_for_db(db_path: Path) -> MagicMock:
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.raw = {
        "database": {
            "enabled": True,
            "persist_transcript_text": False,
            "persist_comment_text": True,
        }
    }
    cfg.database_path = db_path
    return cfg


def test_research_run_persists_full_report(tmp_path: Path) -> None:
    db_path = tmp_path / "srp.db"
    state = _state_with_report(_minimal_report())

    with patch(
        "social_research_probe.config.load_active_config", return_value=_cfg_for_db(db_path)
    ):
        _run(YouTubePersistStage().execute(state))

    conn = open_connection(db_path)
    try:
        run_count = conn.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0]
        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        snap_count = conn.execute("SELECT COUNT(*) FROM source_snapshots").fetchone()[0]
    finally:
        conn.close()

    assert run_count >= 1
    assert source_count >= 1
    assert snap_count >= 1


def test_research_run_persistence_failure_is_non_fatal(tmp_path: Path) -> None:
    db_path = tmp_path / "srp.db"
    state = _state_with_report(_minimal_report())

    with patch(
        "social_research_probe.config.load_active_config", return_value=_cfg_for_db(db_path)
    ):
        with patch(
            "social_research_probe.technologies.persistence.sqlite.open_connection",
            side_effect=sqlite3.OperationalError("simulated disk failure"),
        ):
            result_state = _run(YouTubePersistStage().execute(state))

    assert result_state is not None
    warnings = result_state.outputs["report"].get("warnings", [])
    assert any("persistence" in w for w in warnings)


def test_demo_report_persists_run(tmp_path: Path) -> None:
    from social_research_probe.commands._demo_fixtures import build_demo_report

    db_path = tmp_path / "srp.db"
    report = build_demo_report()
    report.setdefault("warnings", [])
    report.setdefault("export_paths", {})
    state = _state_with_report(report)

    with patch(
        "social_research_probe.config.load_active_config", return_value=_cfg_for_db(db_path)
    ):
        _run(YouTubePersistStage().execute(state))

    conn = open_connection(db_path)
    try:
        run_count = conn.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0]
        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    finally:
        conn.close()

    assert run_count >= 1
    assert source_count >= 1
