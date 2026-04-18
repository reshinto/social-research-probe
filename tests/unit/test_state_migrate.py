"""Version-chain migrators. Idempotent. Backup before overwrite."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.errors import MigrationError
from social_research_probe.state.migrate import migrate_to_current, migrators_for
from social_research_probe.state.schemas import SCHEMA_VERSION


def test_current_version_is_noop(tmp_path: Path):
    path = tmp_path / "topics.json"
    data = {"schema_version": SCHEMA_VERSION, "topics": ["a"]}
    result = migrate_to_current(path, data, kind="topics")
    assert result == data


def test_missing_schema_version_treated_as_zero(tmp_path: Path):
    path = tmp_path / "topics.json"
    data = {"topics": ["a"]}  # no schema_version
    result = migrate_to_current(path, data, kind="topics")
    assert result["schema_version"] == SCHEMA_VERSION


def test_unknown_future_version_raises(tmp_path: Path):
    path = tmp_path / "topics.json"
    data = {"schema_version": 999, "topics": []}
    with pytest.raises(MigrationError):
        migrate_to_current(path, data, kind="topics")


def test_backup_written_before_migration(tmp_path: Path):
    path = tmp_path / "topics.json"
    path.write_text(json.dumps({"topics": ["legacy"]}))
    data = json.loads(path.read_text())
    migrate_to_current(path, data, kind="topics")
    backups = list((tmp_path / ".backups").glob("topics.v0.*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text()) == {"topics": ["legacy"]}


def test_migrators_for_known_kinds():
    assert migrators_for("topics") is not None
    assert migrators_for("purposes") is not None
    assert migrators_for("pending_suggestions") is not None
