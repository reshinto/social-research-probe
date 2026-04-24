"""Atomic writes, default seeding, POSIX os.replace semantics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from social_research_probe.state.store import atomic_write_json, read_json


def test_read_missing_file_seeds_defaults(tmp_path: Path):
    path = tmp_path / "topics.json"
    default = {"schema_version": 1, "topics": []}
    result = read_json(path, default_factory=lambda: default)
    assert result == default
    assert path.exists()
    assert json.loads(path.read_text()) == default


def test_read_existing_file_returns_content(tmp_path: Path):
    path = tmp_path / "topics.json"
    path.write_text(json.dumps({"schema_version": 1, "topics": ["a"]}))
    result = read_json(path, default_factory=lambda: {"x": 1})
    assert result["topics"] == ["a"]


def test_atomic_write_overwrites(tmp_path: Path):
    path = tmp_path / "topics.json"
    atomic_write_json(path, {"v": 1})
    atomic_write_json(path, {"v": 2})
    assert json.loads(path.read_text()) == {"v": 2}


def test_atomic_write_leaves_no_tmp_files(tmp_path: Path):
    path = tmp_path / "topics.json"
    atomic_write_json(path, {"v": 1})
    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert not tmp_files, f"temp files leaked: {tmp_files}"


def test_atomic_write_creates_parent_dir(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "topics.json"
    atomic_write_json(path, {"v": 1})
    assert path.exists()


def test_atomic_write_formatting(tmp_path: Path):
    path = tmp_path / "f.json"
    atomic_write_json(path, {"b": 2, "a": 1})
    content = path.read_text()
    assert content.endswith("\n")
    assert "  " in content  # indent=2


def test_atomic_write_cleans_up_tmp_on_base_exception(tmp_path: Path, monkeypatch) -> None:
    """The except BaseException branch must delete the tmp file and re-raise."""
    import os as _os

    path = tmp_path / "f.json"

    def raise_keyboard_interrupt(src, dst):
        raise KeyboardInterrupt

    monkeypatch.setattr(_os, "replace", raise_keyboard_interrupt)

    with pytest.raises(KeyboardInterrupt):
        atomic_write_json(path, {"v": 1})

    # No tmp files should remain after the cleanup.
    tmp_files = list(tmp_path.glob(".f.json.*.tmp"))
    assert not tmp_files, f"tmp files leaked: {tmp_files}"
