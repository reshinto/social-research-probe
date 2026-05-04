"""Unit tests for demo report SQLite persistence wiring."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from social_research_probe.commands.demo import _persist_if_enabled
from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.utils.demo.fixtures import build_demo_report


def _cfg_for_db(db_path: Path, enabled: bool = True) -> MagicMock:
    cfg = MagicMock()
    cfg.raw = {
        "database": {
            "enabled": enabled,
            "persist_transcript_text": False,
            "persist_comment_text": True,
        }
    }
    cfg.database_path = db_path
    return cfg


def _demo_report_with_paths(tmp_path: Path) -> dict:
    report = build_demo_report()
    report["html_report_path"] = f"file://{tmp_path / 'demo.html'}"
    report["export_paths"] = {
        "sources_csv": str(tmp_path / "demo-sources.csv"),
        "comments_csv": str(tmp_path / "demo-comments.csv"),
    }
    return report


class TestPersistWritesToSqlite:
    def test_persist_writes_to_sqlite_when_enabled(self, tmp_path: Path) -> None:
        db_path = tmp_path / "srp.db"
        cfg = _cfg_for_db(db_path, enabled=True)
        report = _demo_report_with_paths(tmp_path)

        asyncio.run(_persist_if_enabled(report, cfg))

        conn = sqlite3.connect(str(db_path))
        runs = conn.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0]
        sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        snaps = conn.execute("SELECT COUNT(*) FROM source_snapshots").fetchone()[0]
        conn.close()
        assert runs >= 1
        assert sources >= 1
        assert snaps >= 1

    def test_persist_stores_export_paths_as_artifacts(self, tmp_path: Path) -> None:
        db_path = tmp_path / "srp.db"
        cfg = _cfg_for_db(db_path, enabled=True)
        report = _demo_report_with_paths(tmp_path)

        asyncio.run(_persist_if_enabled(report, cfg))

        conn = sqlite3.connect(str(db_path))
        artifacts = conn.execute("SELECT kind FROM artifacts").fetchall()
        kinds = {row[0] for row in artifacts}
        conn.close()
        assert "sources_csv" in kinds
        assert "comments_csv" in kinds

    def test_persist_stores_synthetic_disclaimer_in_warnings_table(self, tmp_path: Path) -> None:
        db_path = tmp_path / "srp.db"
        cfg = _cfg_for_db(db_path, enabled=True)
        report = _demo_report_with_paths(tmp_path)

        asyncio.run(_persist_if_enabled(report, cfg))

        conn = sqlite3.connect(str(db_path))
        warnings = conn.execute("SELECT message FROM warnings").fetchall()
        messages = [row[0] for row in warnings]
        conn.close()
        assert any("Synthetic" in m or "demonstration" in m.lower() for m in messages)


class TestPersistSkipsWhenDisabled:
    def test_persist_skips_when_database_disabled(self, tmp_path: Path) -> None:
        db_path = tmp_path / "srp.db"
        cfg = _cfg_for_db(db_path, enabled=False)
        report = _demo_report_with_paths(tmp_path)

        with patch("social_research_probe.commands.demo.PersistenceService") as mock_svc_cls:
            asyncio.run(_persist_if_enabled(report, cfg))
            mock_svc_cls.assert_not_called()

        assert not db_path.exists()


class TestPersistNonFatalOnFailure:
    def test_persist_non_fatal_on_failure(self, tmp_path: Path) -> None:
        db_path = tmp_path / "srp.db"
        cfg = _cfg_for_db(db_path, enabled=True)
        report = _demo_report_with_paths(tmp_path)

        failed_result = ServiceResult(
            service_name="persistence",
            input_key="test",
            tech_results=[
                TechResult(
                    tech_name="sqlite_persist",
                    input={},
                    output=None,
                    success=False,
                    error="simulated disk failure",
                )
            ],
        )
        with patch("social_research_probe.commands.demo.PersistenceService") as mock_svc_cls:
            mock_instance = MagicMock()
            mock_instance.execute_batch = AsyncMock(return_value=[failed_result])
            mock_svc_cls.return_value = mock_instance
            asyncio.run(_persist_if_enabled(report, cfg))

        assert any("persistence:" in w for w in report.get("warnings", []))
        assert any("simulated disk failure" in w for w in report["warnings"])


class TestRunCallsPersistAfterExports:
    def test_run_calls_persist_after_exports(self) -> None:
        call_order: list[str] = []

        async def fake_render(report: dict) -> None:
            call_order.append("render")
            report["report_path"] = "/tmp/demo.html"

        async def fake_exports(report: dict, cfg: dict, stem: str, d: Path) -> dict[str, str]:
            call_order.append("exports")
            return {"sources_csv": "/tmp/x.csv"}

        async def fake_persist(report: dict, cfg: object) -> None:
            call_order.append("persist")
            assert "export_paths" in report

        with (
            patch("social_research_probe.commands.demo._render_html", side_effect=fake_render),
            patch("social_research_probe.commands.demo._run_exports", side_effect=fake_exports),
            patch(
                "social_research_probe.commands.demo._persist_if_enabled",
                side_effect=fake_persist,
            ),
            patch("social_research_probe.commands.demo._print_paths"),
            patch("social_research_probe.commands.demo.load_active_config") as mock_cfg,
        ):
            import argparse

            from social_research_probe.commands.demo import run

            mock_cfg.return_value = MagicMock()
            mock_cfg.return_value.platform_defaults.return_value = {}
            run(argparse.Namespace())

        assert call_order == ["render", "exports", "persist"]
