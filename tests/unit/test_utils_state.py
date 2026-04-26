"""Tests for utils.state.{store, validate, schemas, migrate}."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.utils.core.errors import MigrationError, ValidationError
from social_research_probe.utils.state import migrate, schemas, store, validate


class TestStore:
    def test_read_seeds_default_when_missing(self, tmp_path):
        path = tmp_path / "topics.json"
        result = store.read_json(path, schemas.default_topics)
        assert result == {"schema_version": 1, "topics": []}
        assert path.exists()

    def test_read_existing(self, tmp_path):
        path = tmp_path / "topics.json"
        path.write_text(json.dumps({"schema_version": 1, "topics": ["a"]}))
        result = store.read_json(path, schemas.default_topics)
        assert result["topics"] == ["a"]

    def test_atomic_write_round_trip(self, tmp_path):
        path = tmp_path / "out.json"
        store.atomic_write_json(path, {"k": "v"})
        assert json.loads(path.read_text())["k"] == "v"

    def test_atomic_write_creates_parents(self, tmp_path):
        path = tmp_path / "nest" / "deep" / "out.json"
        store.atomic_write_json(path, {"k": 1})
        assert path.exists()

    def test_atomic_write_cleans_tmp_on_error(self, tmp_path, monkeypatch):
        path = tmp_path / "x.json"

        def boom(*a, **kw):
            raise RuntimeError("nope")

        monkeypatch.setattr("os.replace", boom)
        with pytest.raises(RuntimeError):
            store.atomic_write_json(path, {"k": 1})
        assert list(tmp_path.glob("*.tmp")) == []


class TestValidate:
    def test_valid_passes(self):
        validate.validate({"schema_version": 1, "topics": []}, schemas.TOPICS_SCHEMA)

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate.validate({"topics": "not-a-list"}, schemas.TOPICS_SCHEMA)

    def test_root_path_label(self):
        with pytest.raises(ValidationError, match="<root>"):
            validate.validate("not-an-object", schemas.TOPICS_SCHEMA)


class TestSchemas:
    def test_default_topics(self):
        assert schemas.default_topics() == {"schema_version": 1, "topics": []}

    def test_default_purposes(self):
        assert schemas.default_purposes() == {"schema_version": 1, "purposes": {}}

    def test_default_pending(self):
        d = schemas.default_pending_suggestions()
        assert d["schema_version"] == 1
        assert d["pending_topic_suggestions"] == []
        assert d["pending_purpose_suggestions"] == []


class TestMigrate:
    def test_unknown_kind_raises(self):
        with pytest.raises(MigrationError):
            migrate.migrators_for("nope")

    def test_migrators_known(self):
        assert len(migrate.migrators_for("topics")) >= 1

    def test_at_current_returns_unchanged(self, tmp_path: Path):
        data = {"schema_version": 1, "topics": []}
        path = tmp_path / "topics.json"
        out = migrate.migrate_to_current(path, data, kind="topics")
        assert out == data

    def test_future_version_raises(self, tmp_path: Path):
        data = {"schema_version": 99}
        path = tmp_path / "topics.json"
        with pytest.raises(MigrationError, match="schema_version=99"):
            migrate.migrate_to_current(path, data, kind="topics")

    def test_v0_to_v1_tags_version_and_writes_backup(self, tmp_path: Path):
        data = {"topics": []}
        path = tmp_path / "topics.json"
        path.write_text("{}")
        out = migrate.migrate_to_current(path, data, kind="topics")
        assert out["schema_version"] == 1
        backups = list((tmp_path / ".backups").glob("topics.v0.*.json"))
        assert len(backups) == 1
