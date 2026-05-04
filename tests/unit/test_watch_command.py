"""Tests for srp watch command behavior."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from social_research_probe.commands import WatchSubcommand
from social_research_probe.commands import watch as watch_cmd
from social_research_probe.commands.watch import run
from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
    get_run_by_text_id,
)
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
from social_research_probe.technologies.persistence.sqlite.watch_repository import (
    insert_alert_event,
    insert_watch,
    insert_watch_run,
    update_watch_after_run,
)
from social_research_probe.utils.core.errors import ValidationError


class _Cfg:
    def __init__(
        self,
        tmp_path: Path,
        *,
        db_enabled: bool = True,
        tech_enabled: bool = True,
        service_enabled: bool = True,
        stage_enabled: bool = True,
    ) -> None:
        self.data_dir = tmp_path
        self.database_path = tmp_path / "srp.db"
        self.raw = {
            "database": {"enabled": db_enabled},
            "notifications": {
                "enabled": True,
                "default_channels": ["file"],
                "file": {"enabled": True, "output_dir": "notifications"},
                "telegram": {
                    "enabled": True,
                    "bot_token_env": "TELEGRAM_BOT_TOKEN",
                    "chat_id_env": "TELEGRAM_CHAT_ID",
                    "timeout_seconds": 10,
                },
            },
        }
        self._tech_enabled = tech_enabled
        self._service_enabled = service_enabled
        self._stage_enabled = stage_enabled

    def technology_enabled(self, name: str) -> bool:
        return name != "sqlite_persist" or self._tech_enabled

    def service_enabled(self, name: str) -> bool:
        return name == "sqlite" and self._service_enabled

    def stage_enabled(self, platform: str, name: str) -> bool:
        return platform == "youtube" and name == "persist" and self._stage_enabled


def _args(**kwargs) -> argparse.Namespace:
    defaults = {"output": "text", "watch_id": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def test_watch_add_list_remove(tmp_path: Path, capsys: object) -> None:
    cfg = _Cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        add_args = _args(
            watch_cmd=WatchSubcommand.ADD,
            topic="AI agents",
            platform="youtube",
            purposes=["latest-news"],
            interval=None,
            alert_rules=[],
            output_dir=None,
            disabled=False,
        )
        assert run(add_args) == 0
        assert run(_args(watch_cmd=WatchSubcommand.LIST, enabled=False)) == 0
    out = capsys.readouterr().out
    watch_id = next(line.split()[0] for line in out.splitlines() if line.startswith("watch-"))
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert run(_args(watch_cmd=WatchSubcommand.REMOVE, watch_id=watch_id)) == 0


def test_watch_run_requires_sqlite_persist_enabled(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path, tech_enabled=False)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError, match="sqlite_persist"):
            run(_args(watch_cmd=WatchSubcommand.RUN))


def test_watch_commands_require_database_enabled(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path, db_enabled=False)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError, match=r"database\.enabled=true"):
            run(_args(watch_cmd=WatchSubcommand.LIST, enabled=False))


def test_watch_run_requires_sqlite_service_enabled(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path, service_enabled=False)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError, match=r"services\.persistence\.sqlite=true"):
            run(_args(watch_cmd=WatchSubcommand.RUN))


def test_watch_run_records_disabled_persist_stage_failure(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path, stage_enabled=False)
    _seed_watch(cfg.database_path, "watch-ai", "AI agents")

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert run(_args(watch_cmd=WatchSubcommand.RUN)) == 2

    conn = _conn(cfg.database_path)
    row = conn.execute("SELECT status, error_message FROM watch_runs").fetchone()
    assert row[0] == "failed"
    assert "stages.youtube.persist=true" in row[1]
    conn.close()


def test_watch_add_requires_purpose(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError, match="at least one --purpose"):
            run(
                _args(
                    watch_cmd=WatchSubcommand.ADD,
                    topic="AI agents",
                    platform="youtube",
                    purposes=[],
                    interval=None,
                    alert_rules=[],
                    output_dir=None,
                    disabled=False,
                )
            )


def test_watch_add_validates_topic_and_platform(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError, match="non-empty --topic"):
            run(
                _args(
                    watch_cmd=WatchSubcommand.ADD,
                    topic=" ",
                    platform="youtube",
                    purposes=["latest-news"],
                    interval=None,
                    alert_rules=[],
                    output_dir=None,
                    disabled=False,
                )
            )
        with pytest.raises(ValidationError, match="unsupported watch platform"):
            run(
                _args(
                    watch_cmd=WatchSubcommand.ADD,
                    topic="AI agents",
                    platform="nope",
                    purposes=["latest-news"],
                    interval=None,
                    alert_rules=[],
                    output_dir=None,
                    disabled=False,
                )
            )


def test_alert_rule_parse_and_watch_id_collision(tmp_path: Path) -> None:
    rules = watch_cmd._parse_rules(
        ['{"metric":"new_claims_count","op":">=","value":2,"severity":"critical"}']
    )
    assert rules[0]["metric"] == "new_claims_count"

    conn = _conn(tmp_path / "srp.db")
    first = watch_cmd._generate_watch_id(conn, "AI agents", "youtube", ["latest-news"])
    with conn:
        insert_watch(
            conn,
            watch_id=first,
            topic="AI agents",
            platform="youtube",
            purposes=["latest-news"],
            enabled=True,
            interval=None,
            alert_rules=rules,
            output_dir=None,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
    assert (
        watch_cmd._generate_watch_id(conn, "AI agents", "youtube", ["latest-news"]) == f"{first}-2"
    )
    conn.close()


def test_watch_remove_missing_raises(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError, match="watch not found"):
            run(_args(watch_cmd=WatchSubcommand.REMOVE, watch_id="missing"))


def test_watch_run_missing_selection_raises(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError, match="watch not found"):
            run(_args(watch_cmd=WatchSubcommand.RUN, watch_id="missing"))


def test_watch_run_records_failure_and_continues(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    _seed_watch(cfg.database_path, "watch-bad", "bad topic")
    _seed_watch(cfg.database_path, "watch-ok", "good topic")

    def fake_research(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
        if topic == "bad topic":
            raise RuntimeError("research failed")
        _insert_run(cfg.database_path, "run-ok", topic)
        return {"run_id": "run-ok"}

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch("social_research_probe.commands.research.run_research_for_watch", fake_research):
            assert run(_args(watch_cmd=WatchSubcommand.RUN)) == 2

    conn = _conn(cfg.database_path)
    statuses = [r[0] for r in conn.execute("SELECT status FROM watch_runs ORDER BY id")]
    assert statuses == ["failed", "success"]
    conn.close()


def test_watch_run_compares_and_persists_alert(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    _seed_watch(cfg.database_path, "watch-ai", "AI agents", output_dir=str(tmp_path / "out"))
    _insert_run(cfg.database_path, "run-base", "AI agents")
    _set_last_target(cfg.database_path, "watch-ai", "run-base")

    def fake_research(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
        _insert_run(cfg.database_path, "run-target", topic, with_source=True)
        return {"run_id": "run-target"}

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch("social_research_probe.commands.research.run_research_for_watch", fake_research):
            with patch(
                "social_research_probe.utils.notifications.dispatcher.dispatch_alert_notifications"
            ) as notify_mock:
                assert run(_args(watch_cmd=WatchSubcommand.RUN, watch_id="watch-ai")) == 0

    conn = _conn(cfg.database_path)
    assert conn.execute("SELECT COUNT(*) FROM alert_events").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notification_deliveries").fetchone()[0] == 0
    assert list((tmp_path / "out").glob("alert-*.json"))
    notify_mock.assert_not_called()
    conn.close()


def test_watch_run_notify_sends_file_delivery(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    _seed_watch(cfg.database_path, "watch-ai", "AI agents", output_dir=str(tmp_path / "out"))
    _insert_run(cfg.database_path, "run-base", "AI agents")
    _set_last_target(cfg.database_path, "watch-ai", "run-base")

    def fake_research(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
        _insert_run(cfg.database_path, "run-target", topic, with_source=True)
        return {"run_id": "run-target"}

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch("social_research_probe.commands.research.run_research_for_watch", fake_research):
            assert (
                run(
                    _args(
                        watch_cmd=WatchSubcommand.RUN,
                        watch_id="watch-ai",
                        notify=True,
                        channels=["file"],
                    )
                )
                == 0
            )

    conn = _conn(cfg.database_path)
    row = conn.execute(
        "SELECT status, channel, artifact_paths_json FROM notification_deliveries"
    ).fetchone()
    assert row[0] == "sent"
    assert row[1] == "file"
    assert "notification_markdown" in row[2]
    conn.close()


def test_watch_run_notify_failure_does_not_fail_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _Cfg(tmp_path)
    _seed_watch(cfg.database_path, "watch-ai", "AI agents", output_dir=str(tmp_path / "out"))
    _insert_run(cfg.database_path, "run-base", "AI agents")
    _set_last_target(cfg.database_path, "watch-ai", "run-base")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    def fake_research(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
        _insert_run(cfg.database_path, "run-target", topic, with_source=True)
        return {"run_id": "run-target"}

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch("social_research_probe.commands.research.run_research_for_watch", fake_research):
            assert (
                run(
                    _args(
                        watch_cmd=WatchSubcommand.RUN,
                        watch_id="watch-ai",
                        notify=True,
                        channels=["telegram"],
                    )
                )
                == 0
            )

    conn = _conn(cfg.database_path)
    assert conn.execute("SELECT status FROM watch_runs").fetchone()[0] == "success"
    delivery = conn.execute("SELECT status, error_message FROM notification_deliveries").fetchone()
    assert delivery[0] == "failed"
    assert "TELEGRAM_BOT_TOKEN" in delivery[1]
    conn.close()


def test_watch_notify_dispatch_exception_is_swallowed(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    conn = _conn(cfg.database_path)

    def boom(
        conn_arg: object, cfg_arg: object, alerts: list[dict], channels: list[str] | None
    ) -> list:
        raise RuntimeError("dispatcher failed")

    try:
        with patch(
            "social_research_probe.utils.notifications.dispatcher.dispatch_alert_notifications",
            boom,
        ):
            result = watch_cmd._notify_alerts(
                conn, cfg, [{"alert_id": "alert-1"}], _args(notify=True, channels=["file"])
            )
    finally:
        conn.close()
    assert result == []


def test_watch_run_due_runs_only_due_enabled_watches(tmp_path: Path, capsys: object) -> None:
    cfg = _Cfg(tmp_path)
    _seed_interval_watch(cfg.database_path, "watch-due", "due topic", "daily", None)
    _seed_interval_watch(
        cfg.database_path, "watch-future", "future topic", "daily", "2999-01-01T00:00:00+00:00"
    )
    _seed_interval_watch(cfg.database_path, "watch-manual", "manual topic", None, None)
    _seed_interval_watch(cfg.database_path, "watch-invalid", "bad topic", "fortnightly", None)
    _seed_interval_watch(
        cfg.database_path, "watch-disabled", "disabled topic", "daily", None, False
    )

    def fake_research(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
        _insert_run(cfg.database_path, "run-due", topic)
        return {"run_id": "run-due"}

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch("social_research_probe.commands.research.run_research_for_watch", fake_research):
            assert run(_args(watch_cmd=WatchSubcommand.RUN_DUE, notify=False)) == 0

    conn = _conn(cfg.database_path)
    assert conn.execute("SELECT COUNT(*) FROM watch_runs").fetchone()[0] == 1
    conn.close()
    out = capsys.readouterr().out
    assert "watch-due ok" in out
    assert "watch-manual skipped: manual-only interval" in out
    assert "watch-invalid skipped: unsupported interval: fortnightly" in out


def test_watch_run_records_missing_run_id_and_missing_target(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    _seed_watch(cfg.database_path, "watch-no-run-id", "no run id")
    _seed_watch(cfg.database_path, "watch-no-target", "no target")

    def fake_research(platform: str, topic: str, purposes: tuple[str, ...]) -> dict:
        if topic == "no run id":
            return {}
        return {"run_id": "missing-run"}

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch("social_research_probe.commands.research.run_research_for_watch", fake_research):
            assert run(_args(watch_cmd=WatchSubcommand.RUN)) == 2

    conn = _conn(cfg.database_path)
    errors = [r[0] for r in conn.execute("SELECT error_message FROM watch_runs ORDER BY id")]
    assert any("target run_id" in e for e in errors)
    assert any("persisted target run not found" in e for e in errors)
    conn.close()


def test_watch_compare_without_output_dir_and_no_matching_alert(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    _insert_run(cfg.database_path, "run-base", "AI agents")
    _insert_run(cfg.database_path, "run-target", "AI agents")
    conn = _conn(cfg.database_path)
    baseline = get_run_by_text_id(conn, "run-base")
    target = get_run_by_text_id(conn, "run-target")
    watch = {
        "watch_id": "watch-ai",
        "topic": "AI agents",
        "platform": "youtube",
        "alert_rules": [{"metric": "new_sources_count", "op": ">=", "value": 99}],
        "output_dir": None,
    }

    comparison, artifacts = watch_cmd._compare_if_possible(
        conn, cfg, watch, _args(export_dir=None), target, baseline
    )
    assert comparison is not None
    assert artifacts == {}
    assert watch_cmd._persist_alerts(conn, cfg, watch, comparison, artifacts) == []
    conn.close()


def test_watch_resolve_baseline_falls_back_when_last_run_missing(tmp_path: Path) -> None:
    _insert_run(tmp_path / "srp.db", "run-base", "AI agents")
    _insert_run(tmp_path / "srp.db", "run-target", "AI agents")
    conn = _conn(tmp_path / "srp.db")
    baseline = watch_cmd._resolve_baseline(
        conn,
        {
            "topic": "AI agents",
            "platform": "youtube",
            "last_target_run_id": "missing-run",
        },
        "run-target",
    )
    assert baseline["run_id"] == "run-base"
    conn.close()


def test_watch_resolve_baseline_uses_prior_successful_watch_run(tmp_path: Path) -> None:
    db_path = tmp_path / "srp.db"
    _seed_watch(db_path, "watch-ai", "AI agents")
    _insert_run(db_path, "run-prior-watch", "AI agents")
    _insert_run(db_path, "run-latest-match", "AI agents")
    _insert_run(db_path, "run-target", "AI agents")
    conn = _conn(db_path)
    with conn:
        conn.execute(
            "UPDATE research_runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01T00:00:01", "run-prior-watch"),
        )
        conn.execute(
            "UPDATE research_runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01T00:00:02", "run-latest-match"),
        )
        conn.execute(
            "UPDATE research_runs SET started_at = ? WHERE run_id = ?",
            ("2026-01-01T00:00:03", "run-target"),
        )
        insert_watch_run(
            conn,
            watch_run_id="watchrun-prior",
            watch_id="watch-ai",
            baseline_run_id=None,
            target_run_id="run-prior-watch",
            started_at="2026-01-01T00:00:01",
            finished_at="2026-01-01T00:01:01",
            status="success",
            error_kind=None,
            error_message=None,
            comparison_artifacts={},
        )
    baseline = watch_cmd._resolve_baseline(
        conn,
        {
            "watch_id": "watch-ai",
            "topic": "AI agents",
            "platform": "youtube",
            "last_target_run_id": "missing-run",
        },
        "run-target",
    )
    assert baseline["run_id"] == "run-prior-watch"
    conn.close()


def test_watch_resolve_baseline_falls_back_when_prior_watch_run_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "srp.db"
    _seed_watch(db_path, "watch-ai", "AI agents")
    _insert_run(db_path, "run-base", "AI agents")
    _insert_run(db_path, "run-target", "AI agents")
    conn = _conn(db_path)
    with conn:
        insert_watch_run(
            conn,
            watch_run_id="watchrun-missing-prior",
            watch_id="watch-ai",
            baseline_run_id=None,
            target_run_id="missing-prior",
            started_at="2026-01-01T00:00:01",
            finished_at="2026-01-01T00:01:01",
            status="success",
            error_kind=None,
            error_message=None,
            comparison_artifacts={},
        )
    baseline = watch_cmd._resolve_baseline(
        conn,
        {
            "watch_id": "watch-ai",
            "topic": "AI agents",
            "platform": "youtube",
            "last_target_run_id": None,
        },
        "run-target",
    )
    assert baseline["run_id"] == "run-base"
    conn.close()


def test_alert_export_failure_still_persists_event(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    _seed_watch(cfg.database_path, "watch-ai", "AI agents")
    conn = _conn(cfg.database_path)
    alert = {
        "alert_id": "alert-export-failed",
        "watch_id": "watch-ai",
        "baseline_run_id": "run-base",
        "target_run_id": "run-target",
        "created_at": "2026-01-01T00:00:00",
        "severity": "warning",
        "title": "New sources",
        "message": "Watch watch-ai detected research changes",
        "matched_rules": [{"metric": "new_sources_count"}],
        "trend_signals": [],
        "artifact_paths": {},
        "acknowledged": False,
    }
    with patch(
        "social_research_probe.utils.monitoring.export.write_alert_artifacts",
        side_effect=OSError("read-only output"),
    ):
        watch_cmd._write_and_insert_alert(conn, cfg, {"output_dir": None}, alert)

    row = conn.execute(
        "SELECT artifact_paths_json FROM alert_events WHERE alert_id = 'alert-export-failed'"
    ).fetchone()
    assert "alert_export_error" in row[0]
    conn.close()


def test_watch_alerts_command_and_output_formats(tmp_path: Path, capsys: object) -> None:
    cfg = _Cfg(tmp_path)
    conn = _conn(cfg.database_path)
    with conn:
        insert_watch(
            conn,
            watch_id="watch-ai",
            topic="AI agents",
            platform="youtube",
            purposes=["latest-news"],
            enabled=True,
            interval=None,
            alert_rules=[],
            output_dir=None,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        insert_alert_event(
            conn,
            alert_id="alert-1",
            watch_id="watch-ai",
            baseline_run_id="run-base",
            target_run_id="run-target",
            created_at="2026-01-01T00:00:00",
            severity="warning",
            title="New sources",
            message="Watch watch-ai detected research changes",
            matched_rules=[{"metric": "new_sources_count"}],
            trend_signals=[],
            artifact_paths={},
            acknowledged=False,
        )
    conn.close()

    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert run(_args(watch_cmd=WatchSubcommand.ALERTS, limit=10, output="text")) == 0

    watch_cmd._print_alert_result([], _args(output="json"))
    watch_cmd._print_alert_result([], _args(output="markdown"))
    watch_cmd._print_alert_result(
        [{"alert_id": "alert-1", "severity": "warning", "watch_id": "watch-ai", "title": "New"}],
        _args(output="markdown"),
    )
    out = capsys.readouterr().out
    assert "alert-1" in out
    assert "No alerts found." in out


def test_watch_result_output_formats(capsys: object) -> None:
    watch = {
        "watch_id": "watch-ai",
        "enabled": False,
        "platform": "youtube",
        "topic": "AI agents",
        "purposes": ["latest-news"],
    }

    watch_cmd._print_watch_result(watch, _args(output="json"))
    watch_cmd._print_watch_result([watch], _args(output="markdown"))
    watch_cmd._print_run_result(
        [{"watch_id": "watch-ai", "status": "success", "target_run_id": "run-1", "alert_count": 0}],
        _args(output="json"),
    )

    assert watch_cmd._format_watch_markdown(watch) == watch_cmd._format_watch_text(watch)
    assert watch_cmd._format_alert_text([]) == "No alerts found."
    assert watch_cmd._format_run_text([]) == "No enabled watches found."
    assert "skipped" in watch_cmd._format_run_text(
        [{"watch_id": "watch-ai", "status": "skipped", "reason": "manual-only interval"}]
    )
    assert "watch-ai" in capsys.readouterr().out


def test_watch_run_without_subcommand_and_unknown_subcommand() -> None:
    parser = argparse.ArgumentParser()
    with patch.object(parser, "print_help") as print_help:
        assert run(_args(watch_cmd=None, _watch_parser=parser)) == 0
    print_help.assert_called_once()
    assert run(_args(watch_cmd=None, _watch_parser=None)) == 0
    assert run(_args(watch_cmd="bogus")) == 2


def _seed_watch(db_path: Path, watch_id: str, topic: str, output_dir: str | None = None) -> None:
    conn = _conn(db_path)
    with conn:
        insert_watch(
            conn,
            watch_id=watch_id,
            topic=topic,
            platform="youtube",
            purposes=["latest-news"],
            enabled=True,
            interval=None,
            alert_rules=[{"metric": "new_sources_count", "op": ">=", "value": 1}],
            output_dir=output_dir,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
    conn.close()


def _seed_interval_watch(
    db_path: Path,
    watch_id: str,
    topic: str,
    interval: str | None,
    last_run_at: str | None,
    enabled: bool = True,
) -> None:
    conn = _conn(db_path)
    with conn:
        insert_watch(
            conn,
            watch_id=watch_id,
            topic=topic,
            platform="youtube",
            purposes=["latest-news"],
            enabled=enabled,
            interval=interval,
            alert_rules=[],
            output_dir=None,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        if last_run_at is not None:
            conn.execute(
                "UPDATE watches SET last_run_at = ?, last_target_run_id = 'run-old' WHERE watch_id = ?",
                (last_run_at, watch_id),
            )
    conn.close()


def _set_last_target(db_path: Path, watch_id: str, run_id: str) -> None:
    conn = _conn(db_path)
    with conn:
        update_watch_after_run(
            conn,
            watch_id=watch_id,
            last_run_at="2026-01-01T00:00:00",
            last_target_run_id=run_id,
            updated_at="2026-01-01T00:00:00",
        )
    conn.close()


def _insert_run(db_path: Path, run_id: str, topic: str, *, with_source: bool = False) -> None:
    conn = _conn(db_path)
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO research_runs (run_id, topic, platform, started_at, schema_version) "
            "VALUES (?, ?, 'youtube', ?, 5)",
            (run_id, topic, f"2026-01-01T00:00:{len(run_id):02d}"),
        )
        run_pk = conn.execute(
            "SELECT id FROM research_runs WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        if with_source:
            _insert_source_snapshot(conn, run_pk)
    conn.close()


def _insert_source_snapshot(conn: sqlite3.Connection, run_pk: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO sources (platform, external_id, url, first_seen_at, last_seen_at) "
        "VALUES ('youtube', 'vid-target', 'https://youtu.be/target', '2026', '2026')"
    )
    source_pk = conn.execute("SELECT id FROM sources WHERE external_id='vid-target'").fetchone()[0]
    conn.execute(
        "INSERT OR IGNORE INTO source_snapshots (source_id, run_id, observed_at) VALUES (?, ?, '2026')",
        (source_pk, run_pk),
    )
