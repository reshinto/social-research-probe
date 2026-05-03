"""Tests for srp db init/stats/path command handlers."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from social_research_probe.commands.db import run


def _args(db_cmd: str | None = None, db_parser=None) -> argparse.Namespace:
    ns = argparse.Namespace(db_cmd=db_cmd)
    if db_parser is not None:
        ns._db_parser = db_parser
    return ns


def _mock_cfg(tmp_path: Path) -> object:
    from unittest.mock import MagicMock

    cfg = MagicMock()
    cfg.database_path = tmp_path / "srp.db"
    return cfg


# --- db path ---


def test_db_path_prints_resolved_path(tmp_path: Path, capsys):
    with patch("social_research_probe.config.load_active_config", return_value=_mock_cfg(tmp_path)):
        result = run(_args("path"))

    assert result == 0
    assert str(tmp_path / "srp.db") in capsys.readouterr().out


def test_db_path_uses_absolute_override(tmp_path: Path, capsys):
    override = tmp_path / "custom" / "srp.db"
    cfg = _mock_cfg(tmp_path)
    cfg.database_path = override
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        result = run(_args("path"))

    assert result == 0
    assert str(override) in capsys.readouterr().out


# --- db init ---


def test_db_init_creates_db_file(tmp_path: Path, capsys):
    with patch("social_research_probe.config.load_active_config", return_value=_mock_cfg(tmp_path)):
        result = run(_args("init"))

    assert result == 0
    assert (tmp_path / "srp.db").exists()
    out = capsys.readouterr().out
    assert "Database ready" in out
    assert "schema v3" in out


def test_db_init_is_idempotent(tmp_path: Path):
    with patch("social_research_probe.config.load_active_config", return_value=_mock_cfg(tmp_path)):
        assert run(_args("init")) == 0
        assert run(_args("init")) == 0


def test_db_init_creates_parent_directory(tmp_path: Path, capsys):
    nested = tmp_path / "deep" / "nested"
    cfg = _mock_cfg(tmp_path)
    cfg.database_path = nested / "srp.db"
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        result = run(_args("init"))

    assert result == 0
    assert (nested / "srp.db").exists()


# --- db stats ---


def test_db_stats_friendly_message_when_db_missing(tmp_path: Path, capsys):
    with patch("social_research_probe.config.load_active_config", return_value=_mock_cfg(tmp_path)):
        result = run(_args("stats"))

    assert result == 0
    assert "srp db init" in capsys.readouterr().out


def test_db_stats_prints_zero_counts_for_fresh_db(tmp_path: Path, capsys):
    cfg = _mock_cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        run(_args("init"))
        result = run(_args("stats"))

    assert result == 0
    out = capsys.readouterr().out
    assert "research_runs: 0" in out
    assert "sources: 0" in out
    assert "source_snapshots: 0" in out
    assert "comments: 0" in out
    assert "transcripts: 0" in out
    assert "text_surrogates: 0" in out
    assert "warnings: 0" in out
    assert "artifacts: 0" in out
    assert "claims: 0" in out
    assert "claim_reviews: 0" in out
    assert "claim_notes: 0" in out


def test_db_stats_reports_counts_after_seeded_run(tmp_path: Path, capsys):
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema

    db_path = tmp_path / "srp.db"
    conn = open_connection(db_path)
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO research_runs "
        "(run_id, topic, platform, started_at, schema_version) "
        "VALUES ('r1', 'test', 'youtube', '2026-01-01', 1)"
    )
    conn.commit()
    conn.close()

    cfg = _mock_cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        result = run(_args("stats"))

    assert result == 0
    assert "research_runs: 1" in capsys.readouterr().out


# --- db no action ---


def test_db_no_action_prints_help(capsys):
    mock_parser = argparse.ArgumentParser(prog="srp db")
    result = run(_args(db_cmd=None, db_parser=mock_parser))

    assert result == 0
    out = capsys.readouterr().out
    assert "srp db" in out


def test_db_no_action_without_parser_still_returns_zero():
    result = run(_args(db_cmd=None))
    assert result == 0


def test_db_unknown_subcommand_returns_error():
    result = run(_args(db_cmd="unknown-action"))
    assert result == 2
