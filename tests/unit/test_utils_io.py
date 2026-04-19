"""
Tests for ``social_research_probe.utils.io``.

Verifies that ``read_json`` handles existing and missing files correctly (with
and without a default), and that ``write_json`` creates files atomically (no
leftover ``.tmp`` file), creates parent directories automatically, and writes
the correct content.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.utils.io import read_json, write_json


def test_read_json_existing(tmp_path: Path) -> None:
    """read_json must return the parsed content of an existing JSON file."""
    data = {"name": "alice", "score": 42}
    target = tmp_path / "data.json"
    target.write_text(json.dumps(data), encoding="utf-8")

    result = read_json(target)
    assert result == data


def test_read_json_missing_returns_default(tmp_path: Path) -> None:
    """read_json must return a *copy* of the provided default when the file is absent."""
    default = {"fallback": True}
    result = read_json(tmp_path / "nonexistent.json", default=default)

    assert result == default
    # Must be a copy, not the same object, to avoid shared-state bugs.
    assert result is not default


def test_read_json_missing_no_default_returns_empty_dict(tmp_path: Path) -> None:
    """read_json must return an empty dict when the file is absent and no default is given."""
    result = read_json(tmp_path / "nonexistent.json")
    assert result == {}


def test_write_json_creates_file(tmp_path: Path) -> None:
    """write_json must create the file with the correct JSON content."""
    data = {"platform": "youtube", "count": 7}
    target = tmp_path / "output.json"

    write_json(target, data)

    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == data


def test_write_json_atomic(tmp_path: Path) -> None:
    """After a successful write no ``.tmp`` sibling file must remain."""
    target = tmp_path / "output.json"
    write_json(target, {"x": 1})

    tmp_file = target.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_write_json_creates_parent_dirs(tmp_path: Path) -> None:
    """write_json must create any missing parent directories automatically."""
    nested = tmp_path / "a" / "b" / "c" / "data.json"
    write_json(nested, {"nested": True})

    assert nested.exists()
    assert json.loads(nested.read_text(encoding="utf-8")) == {"nested": True}


def test_write_json_cleans_up_tmp_on_error(tmp_path: Path, monkeypatch) -> None:
    """On write failure the .tmp file must be cleaned up and the exception re-raised."""
    import os as _os

    target = tmp_path / "output.json"
    tmp_file = target.with_suffix(".tmp")


    def exploding_replace(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(_os, "replace", exploding_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        write_json(target, {"x": 1})

    # The .tmp file must have been cleaned up (best-effort unlink).
    assert not tmp_file.exists()
