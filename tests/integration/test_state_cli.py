"""End-to-end CLI dispatch for state commands."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from social_research_probe.commands import Command, ConfigSubcommand, ResearchCommand
from social_research_probe.cli.parsers import Arg


def _run(data_dir: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **__import__("os").environ,
        "SRP_DATA_DIR": str(data_dir),
    }
    return subprocess.run(
        [sys.executable, "-m", "social_research_probe.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        input=stdin,
    )


def test_show_topics_empty(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    result = _run(data_dir, Command.SHOW_TOPICS)
    assert result.returncode == 0
    assert "(no topics)" in result.stdout or result.stdout.strip() == ""


def test_add_then_show(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    add = _run(data_dir, Command.UPDATE_TOPICS, Arg.ADD, '"ai agents"|"robotics"')
    assert add.returncode == 0, add.stderr
    show = _run(data_dir, Command.SHOW_TOPICS, Arg.OUTPUT, "json")
    assert show.returncode == 0
    payload = json.loads(show.stdout)
    assert sorted(payload["topics"]) == ["ai agents", "robotics"]


def test_duplicate_add_exits_3(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    _run(data_dir, Command.UPDATE_TOPICS, Arg.ADD, '"ai agents"')
    result = _run(data_dir, Command.UPDATE_TOPICS, Arg.ADD, '"ai agents"')
    assert result.returncode == 3
    assert "duplicate" in result.stderr.lower() or "near-duplicate" in result.stderr.lower()


def test_config_check_secrets_json(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    result = _run(
        data_dir,
        "config",
        ConfigSubcommand.CHECK_SECRETS,
        Arg.NEEDED_FOR,
        ResearchCommand.RESEARCH,
        Arg.PLATFORM,
        "youtube",
        Arg.OUTPUT,
        "json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "youtube_api_key" in payload["missing"]


def test_config_set_secret_from_stdin(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    result = _run(
        data_dir,
        "config",
        ConfigSubcommand.SET_SECRET,
        "youtube_api_key",
        Arg.FROM_STDIN,
        stdin="AIzaSECRETVALUE12345",
    )
    assert result.returncode == 0
    check = _run(
        data_dir,
        "config",
        ConfigSubcommand.CHECK_SECRETS,
        Arg.NEEDED_FOR,
        ResearchCommand.RESEARCH,
        Arg.PLATFORM,
        "youtube",
        Arg.OUTPUT,
        "json",
    )
    payload = json.loads(check.stdout)
    assert "youtube_api_key" in payload["present"]


def test_suggest_and_apply(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    suggest = _run(data_dir, ResearchCommand.SUGGEST_TOPICS, Arg.COUNT, "2", Arg.OUTPUT, "json")
    assert suggest.returncode == 0
    show_pending = _run(data_dir, Command.SHOW_PENDING, Arg.OUTPUT, "json")
    pending = json.loads(show_pending.stdout)
    assert len(pending["pending_topic_suggestions"]) >= 1
    apply = _run(data_dir, Command.APPLY_PENDING, Arg.TOPICS, "all")
    assert apply.returncode == 0
    topics = _run(data_dir, Command.SHOW_TOPICS, Arg.OUTPUT, "json")
    assert json.loads(topics.stdout)["topics"]
