"""Purposes CRUD: method string required on add; dedupe on name."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.commands.purposes import (
    add_purpose,
    remove_purposes,
    rename_purpose,
    show_purposes,
)
from social_research_probe.errors import DuplicateError, ValidationError


def _read(data_dir: Path) -> dict:
    return json.loads((data_dir / "purposes.json").read_text())


def test_add_new_purpose(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="Track emergence", force=False)
    state = _read(tmp_data_dir)
    assert "trends" in state["purposes"]
    assert state["purposes"]["trends"]["method"] == "Track emergence"
    assert state["purposes"]["trends"]["evidence_priorities"] == []


def test_add_duplicate_name_exits_3(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="Track", force=False)
    with pytest.raises(DuplicateError):
        add_purpose(tmp_data_dir, name="trends", method="Different", force=False)


def test_add_requires_nonempty_method(tmp_data_dir: Path):
    with pytest.raises(ValidationError):
        add_purpose(tmp_data_dir, name="trends", method="", force=False)


def test_remove(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    add_purpose(tmp_data_dir, name="career", method="y", force=False)
    remove_purposes(tmp_data_dir, ["trends"])
    state = _read(tmp_data_dir)
    assert list(state["purposes"].keys()) == ["career"]


def test_rename(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    rename_purpose(tmp_data_dir, "trends", "trend-analysis")
    state = _read(tmp_data_dir)
    assert "trends" not in state["purposes"]
    assert "trend-analysis" in state["purposes"]


def test_show(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    assert show_purposes(tmp_data_dir) == {"trends": {"method": "x", "evidence_priorities": [], "scoring_overrides": {}}}
