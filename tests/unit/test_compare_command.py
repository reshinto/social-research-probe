"""Tests for srp compare CLI command."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

from social_research_probe.commands import CompareSubcommand
from social_research_probe.commands.compare import _build_run_info, run
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
from social_research_probe.utils.core.exit_codes import ExitCode


def _setup_db(tmp_path: Path) -> Path:
    """Create a seeded test database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)

    conn.execute(
        "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
        "VALUES (?, ?, ?, ?, ?)",
        ("run-aaa", "AI agents", "youtube", "2024-01-01T00:00:00", 4),
    )
    conn.execute(
        "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
        "VALUES (?, ?, ?, ?, ?)",
        ("run-bbb", "AI agents", "youtube", "2024-01-02T00:00:00", 4),
    )
    conn.execute(
        "INSERT INTO research_runs (run_id, topic, platform, started_at, finished_at, schema_version) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("run-ccc", "AI agents", "youtube", "2024-01-03T00:00:00", "2024-01-03T01:00:00", 4),
    )
    conn.execute(
        "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
        "VALUES (?, ?, ?, ?, ?)",
        ("run-ddd", "AI agents", "youtube", "", 4),
    )
    conn.commit()
    conn.close()
    return db_path


def _mock_config(db_path: Path):
    """Create a mock config that returns the given db_path."""

    class _Cfg:
        database_path = db_path

    return patch(
        "social_research_probe.config.load_active_config",
        return_value=_Cfg(),
    )


def _args(**kwargs) -> argparse.Namespace:
    defaults = {"output": "text", "export_dir": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_build_run_info_wrapper() -> None:
    row = {
        "id": 1,
        "run_id": "run-1",
        "topic": "AI",
        "platform": "youtube",
        "started_at": "s",
        "finished_at": "f",
    }
    counts = {"sources": 1, "claims": 2, "narratives": 3}
    assert _build_run_info(row, counts)["claim_count"] == 2


class TestRunDispatch:
    def test_no_subcommand_prints_help(self, capsys: object) -> None:
        from unittest.mock import Mock

        mock_parser = Mock()
        args = _args(compare_cmd=None, _compare_parser=mock_parser)
        code = run(args)
        assert code == ExitCode.SUCCESS
        mock_parser.print_help.assert_called_once()

    def test_no_subcommand_no_parser(self) -> None:
        args = _args(compare_cmd=None, _compare_parser=None)
        code = run(args)
        assert code == ExitCode.SUCCESS

    def test_invalid_subcommand(self) -> None:
        args = _args(compare_cmd="invalid")
        code = run(args)
        assert code == ExitCode.ERROR


class TestCompareList:
    def test_lists_runs(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.LIST, topic=None, platform=None, limit=20)
            code = run(args)
        assert code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "run-aaa" in captured.out
        assert "run-bbb" in captured.out
        assert "run-ccc" in captured.out
        assert "run-ddd" in captured.out

    def test_lists_runs_json(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(
                compare_cmd=CompareSubcommand.LIST,
                topic=None,
                platform=None,
                limit=20,
                output="json",
            )
            code = run(args)
        assert code == ExitCode.SUCCESS
        data = json.loads(capsys.readouterr().out)
        assert len(data) == 4

    def test_missing_db(self, tmp_path: Path, capsys: object) -> None:
        db_path = tmp_path / "nonexistent.db"
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.LIST, topic=None, platform=None, limit=20)
            code = run(args)
        assert code == ExitCode.ERROR
        assert "Database not found" in capsys.readouterr().out

    def test_lists_empty_runs(self, tmp_path: Path, capsys: object) -> None:
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        ensure_schema(conn)
        conn.commit()
        conn.close()
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.LIST, topic=None, platform=None, limit=20)
            code = run(args)
        assert code == ExitCode.SUCCESS
        assert "No runs found" in capsys.readouterr().out


class TestCompareLatest:
    def test_compares_latest_pair(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.LATEST, topic=None, platform=None)
            code = run(args)
        assert code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "run-bbb" in captured.out
        assert "run-ccc" in captured.out

    def test_missing_db(self, tmp_path: Path, capsys: object) -> None:
        db_path = tmp_path / "nonexistent.db"
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.LATEST, topic=None, platform=None)
            code = run(args)
        assert code == ExitCode.ERROR
        assert "Database not found" in capsys.readouterr().out

    def test_fewer_than_two_runs(self, tmp_path: Path, capsys: object) -> None:
        db_path = tmp_path / "one.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
            "VALUES (?, ?, ?, ?, ?)",
            ("only-one", "AI", "youtube", "2024-01-01T00:00:00", 4),
        )
        conn.commit()
        conn.close()
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.LATEST, topic=None, platform=None)
            code = run(args)
        assert code == ExitCode.ERROR
        assert "Need at least 2 runs" in capsys.readouterr().out

    def test_json_output(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(
                compare_cmd=CompareSubcommand.LATEST, topic=None, platform=None, output="json"
            )
            code = run(args)
        assert code == ExitCode.SUCCESS
        data = json.loads(capsys.readouterr().out)
        assert "baseline" in data
        assert "target" in data


class TestCompareRun:
    def test_compare_by_text_id(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.RUN, run_a="run-aaa", run_b="run-bbb")
            code = run(args)
        assert code == ExitCode.SUCCESS
        captured = capsys.readouterr()
        assert "run-aaa" in captured.out

    def test_compare_by_pk(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.RUN, run_a="1", run_b="2")
            code = run(args)
        assert code == ExitCode.SUCCESS

    def test_missing_db(self, tmp_path: Path, capsys: object) -> None:
        db_path = tmp_path / "nonexistent.db"
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.RUN, run_a="run-aaa", run_b="run-bbb")
            code = run(args)
        assert code == ExitCode.ERROR
        assert "Database not found" in capsys.readouterr().out

    def test_invalid_run_a(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.RUN, run_a="nonexistent", run_b="run-bbb")
            code = run(args)
        assert code == ExitCode.ERROR
        assert "not found" in capsys.readouterr().out

    def test_invalid_run_b(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.RUN, run_a="run-aaa", run_b="nonexistent")
            code = run(args)
        assert code == ExitCode.ERROR
        assert "not found" in capsys.readouterr().out

    def test_invalid_run_integer(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.RUN, run_a="999", run_b="run-bbb")
            code = run(args)
        assert code == ExitCode.ERROR
        assert "not found" in capsys.readouterr().out

    def test_compare_run_ccc_ddd(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        with _mock_config(db_path):
            args = _args(compare_cmd=CompareSubcommand.RUN, run_a="run-ccc", run_b="run-ddd")
            code = run(args)
        assert code == ExitCode.SUCCESS

    def test_export_dir(self, tmp_path: Path, capsys: object) -> None:
        db_path = _setup_db(tmp_path)
        export_dir = tmp_path / "exports"
        with _mock_config(db_path):
            args = _args(
                compare_cmd=CompareSubcommand.RUN,
                run_a="run-aaa",
                run_b="run-bbb",
                export_dir=str(export_dir),
            )
            code = run(args)
        assert code == ExitCode.SUCCESS
        assert export_dir.exists()
        csv_files = list(export_dir.glob("*.csv"))
        assert len(csv_files) == 3
