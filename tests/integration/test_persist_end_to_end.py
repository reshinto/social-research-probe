"""Integration tests for end-to-end SQLite persistence via YouTubePersistStage."""

from __future__ import annotations

import asyncio
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import YouTubePersistStage
from social_research_probe.technologies.persistence.sqlite.connection import open_connection

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _minimal_report(topic: str = "ai agents", html_report_path: str | None = None) -> dict:
    r: dict = {
        "topic": topic,
        "platform": "youtube",
        "purpose_set": ["trends"],
        "items_top_n": [_minimal_item()],
        "warnings": [],
        "export_paths": {},
    }
    if html_report_path:
        r["html_report_path"] = html_report_path
    return r


def _state_with_report(report: dict) -> PipelineState:
    state = PipelineState(platform_type="youtube", cmd=None, cache=None, platform_config={})
    state.outputs["report"] = report
    return state


def _cfg_for_db(db_path: Path, enabled: bool = True) -> MagicMock:
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.raw = {
        "database": {
            "enabled": enabled,
            "persist_transcript_text": False,
            "persist_comment_text": True,
        }
    }
    cfg.database_path = db_path
    return cfg


def _srp_stats(data_dir: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "SRP_DATA_DIR": str(data_dir)}
    return subprocess.run(
        [sys.executable, "-m", "social_research_probe.cli", "db", "stats"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


# --- full report persisted ---


def test_research_run_persists_full_report(tmp_path: Path) -> None:
    db_path = tmp_path / "srp.db"
    html_path = str(tmp_path / "report.html")
    state = _state_with_report(_minimal_report(html_report_path=html_path))

    with patch(
        "social_research_probe.config.load_active_config", return_value=_cfg_for_db(db_path)
    ):
        _run(YouTubePersistStage().execute(state))

    conn = open_connection(db_path)
    try:
        run_count = conn.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0]
        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        snap_count = conn.execute("SELECT COUNT(*) FROM source_snapshots").fetchone()[0]
        artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    finally:
        conn.close()

    assert run_count >= 1
    assert source_count >= 1
    assert snap_count >= 1
    assert artifact_count >= 1


# --- persistence disabled = no DB created ---


def test_persistence_disabled_no_db_writes(tmp_path: Path) -> None:
    db_path = tmp_path / "srp.db"
    state = _state_with_report(_minimal_report())

    with patch(
        "social_research_probe.config.load_active_config",
        return_value=_cfg_for_db(db_path, enabled=False),
    ):
        _run(YouTubePersistStage().execute(state))

    assert not db_path.exists()


# --- persistence failure is non-fatal ---


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


# --- srp db stats sees persisted rows ---


def test_srp_db_stats_shows_persisted_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "srp.db"
    state = _state_with_report(_minimal_report())

    with patch(
        "social_research_probe.config.load_active_config", return_value=_cfg_for_db(db_path)
    ):
        _run(YouTubePersistStage().execute(state))

    result = _srp_stats(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "research_runs: 1" in result.stdout
    assert "sources: 1" in result.stdout
    assert "source_snapshots: 1" in result.stdout


# --- demo report persists ---


def test_demo_report_persists_run(tmp_path: Path) -> None:
    from social_research_probe.utils.demo.fixtures import build_demo_report

    db_path = tmp_path / "srp.db"
    report = build_demo_report()
    report.setdefault("warnings", [])
    report["html_report_path"] = str(tmp_path / "demo_report.html")
    state = _state_with_report(report)

    with patch(
        "social_research_probe.config.load_active_config", return_value=_cfg_for_db(db_path)
    ):
        _run(YouTubePersistStage().execute(state))

    conn = open_connection(db_path)
    try:
        run_count = conn.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0]
        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        artifact_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    finally:
        conn.close()

    assert run_count >= 1
    assert source_count >= 1
    assert artifact_count >= 1
