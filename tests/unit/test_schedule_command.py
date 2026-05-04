"""Tests for local schedule helper commands."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from social_research_probe.commands import ScheduleSubcommand
from social_research_probe.commands import schedule as schedule_cmd
from social_research_probe.utils.monitoring.schedule import (
    cron_schedule,
    due_status,
    interval_seconds,
    supported_intervals,
)


class _Cfg:
    def __init__(self, tmp_path: Path, interval: str = "daily") -> None:
        self.data_dir = tmp_path
        self.raw = {"schedule": {"default_interval": interval}}


def _args(**kwargs: object) -> argparse.Namespace:
    defaults = {"schedule_cmd": ScheduleSubcommand.CRON, "interval": None, "output_path": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_due_status_interval_rules() -> None:
    now = datetime(2026, 1, 2, tzinfo=UTC)
    assert due_status({"interval": None}, now)[0] is False
    assert due_status({"interval": "daily", "last_run_at": None}, now)[0] is True
    assert due_status({"interval": "fortnightly"}, now) == (
        False,
        "unsupported interval: fortnightly",
    )
    invalid = due_status({"interval": "daily", "last_run_at": "bad-date"}, now)
    assert invalid == (False, "invalid last_run_at: bad-date")
    due = due_status({"interval": "daily", "last_run_at": "2026-01-01T00:00:00+00:00"}, now)
    assert due == (True, "due after daily")
    not_due = due_status({"interval": "weekly", "last_run_at": "2026-01-01T00:00:00"}, now)
    assert not_due[0] is False


def test_interval_helpers() -> None:
    assert interval_seconds("hourly") == 3600
    assert interval_seconds("daily") == 86400
    assert interval_seconds("weekly") == 604800
    assert interval_seconds("bad") == 86400
    assert cron_schedule("hourly") == "0 * * * *"
    assert cron_schedule("weekly") == "0 9 * * 1"
    assert cron_schedule("daily") == "0 9 * * *"
    assert supported_intervals() == ("hourly", "daily", "weekly")


def test_schedule_cron_prints_data_dir(tmp_path: Path, capsys: object) -> None:
    cfg = _Cfg(tmp_path, "hourly")
    executable = tmp_path / ".venv" / "bin" / "srp"
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch.object(schedule_cmd.sys, "argv", [str(executable), "schedule", "cron"]):
            assert schedule_cmd.run(_args(schedule_cmd=ScheduleSubcommand.CRON)) == 0
    out = capsys.readouterr().out
    assert "watch run-due --notify" in out
    assert "--data-dir" in out
    assert str(tmp_path) in out
    assert str(executable) in out


def test_schedule_current_executable_bare_command_fallbacks() -> None:
    with patch.object(schedule_cmd.sys, "argv", ["srp"]):
        with patch.object(schedule_cmd.shutil, "which", return_value="/opt/bin/srp"):
            assert schedule_cmd._current_executable() == "/opt/bin/srp"
        with patch.object(schedule_cmd.shutil, "which", return_value=None):
            assert schedule_cmd._current_executable() == "srp"


def test_schedule_launchd_prints_and_writes(tmp_path: Path, capsys: object) -> None:
    cfg = _Cfg(tmp_path)
    output = tmp_path / "watch.plist"
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert schedule_cmd.run(_args(schedule_cmd=ScheduleSubcommand.LAUNCHD)) == 0
        assert (
            schedule_cmd.run(
                _args(schedule_cmd=ScheduleSubcommand.LAUNCHD, output_path=str(output))
            )
            == 0
        )
    out = capsys.readouterr().out
    assert '<plist version="1.0">' in out
    assert "Wrote launchd plist" in out
    assert "ProgramArguments" in output.read_text(encoding="utf-8")


def test_schedule_no_action_and_unknown() -> None:
    parser = argparse.ArgumentParser(prog="srp schedule")
    with patch.object(parser, "print_help") as print_help:
        assert schedule_cmd.run(_args(schedule_cmd=None, _schedule_parser=parser)) == 0
    print_help.assert_called_once()
    assert schedule_cmd.run(_args(schedule_cmd=None, _schedule_parser=None)) == 0
    assert schedule_cmd.run(_args(schedule_cmd="bogus")) == 2


def test_schedule_invalid_config_interval_falls_back(tmp_path: Path, capsys: object) -> None:
    cfg = _Cfg(tmp_path, "bad")
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert schedule_cmd.run(_args(schedule_cmd=ScheduleSubcommand.CRON)) == 0
    cfg.raw = []
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert schedule_cmd.run(_args(schedule_cmd=ScheduleSubcommand.CRON)) == 0
    cfg.raw = {"schedule": {"default_interval": 3}}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert schedule_cmd.run(_args(schedule_cmd=ScheduleSubcommand.CRON)) == 0
    out = capsys.readouterr().out
    assert out.count("0 9 * * *") == 3
