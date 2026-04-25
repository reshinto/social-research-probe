"""Purposes CRUD: method string required on add; dedupe on name."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from social_research_probe.utils.core.errors import DuplicateError, SrpError, ValidationError

from social_research_probe.commands import (
    add_purpose,
    remove_purposes,
    rename_purpose,
    show_purposes,
)


def _read(data_dir: Path) -> dict:
    return json.loads((data_dir / "purposes.json").read_text())


def test_add_new_purpose(tmp_data_dir: Path):
    add_purpose(name="trends", method="Track emergence", force=False)
    state = _read(tmp_data_dir)
    assert "trends" in state["purposes"]
    assert state["purposes"]["trends"]["method"] == "Track emergence"
    assert state["purposes"]["trends"]["evidence_priorities"] == []


def test_add_duplicate_name_exits_3(tmp_data_dir: Path):
    add_purpose(name="trends", method="Track", force=False)
    with pytest.raises(DuplicateError):
        add_purpose(name="trends", method="Different", force=False)


def test_add_requires_nonempty_method(tmp_data_dir: Path):
    with pytest.raises(ValidationError):
        add_purpose(name="trends", method="", force=False)


def test_remove(tmp_data_dir: Path):
    add_purpose(name="trends", method="x", force=False)
    add_purpose(name="career", method="y", force=False)
    remove_purposes(["trends"])
    state = _read(tmp_data_dir)
    assert list(state["purposes"].keys()) == ["career"]


def test_rename(tmp_data_dir: Path):
    add_purpose(name="trends", method="x", force=False)
    rename_purpose("trends", "trend-analysis")
    state = _read(tmp_data_dir)
    assert "trends" not in state["purposes"]
    assert "trend-analysis" in state["purposes"]


def test_show(tmp_data_dir: Path):
    add_purpose(name="trends", method="x", force=False)
    assert show_purposes() == {
        "trends": {"method": "x", "evidence_priorities": [], "scoring_overrides": {}}
    }


def test_rename_onto_existing_raises(tmp_data_dir: Path):
    add_purpose(name="trends", method="x", force=False)
    add_purpose(name="career", method="y", force=False)
    with pytest.raises(DuplicateError):
        rename_purpose("trends", "career")


def test_rename_nonexistent_old_raises(tmp_data_dir: Path):
    with pytest.raises(SrpError):
        rename_purpose("nonexistent", "something")


def test_add_near_duplicate_raises(tmp_data_dir: Path):
    """Line 36: NEAR_DUPLICATE without force raises DuplicateError."""
    add_purpose(name="track latest news channel", method="Track news", force=False)
    # "track latest news channels" scores ~98 with rapidfuzz token_set_ratio → near-duplicate
    with pytest.raises(DuplicateError):
        add_purpose(name="track latest news channels", method="Track news too", force=False)


def test_add_existing_with_force_raises(tmp_data_dir: Path):
    """Line 43: existing name with force=True raises DuplicateError (can't overwrite, use rename)."""
    add_purpose(name="trends", method="original", force=False)
    with pytest.raises(DuplicateError, match="use rename"):
        add_purpose(name="trends", method="updated", force=True)


def test_add_near_duplicate_without_force_raises_on_near_dup(tmp_data_dir: Path):
    """Line 36: NEAR_DUPLICATE branch raises when not forced (using known near-dup pair)."""
    add_purpose(name="audience-fit", method="Audience fit analysis", force=False)
    # "audience fit" vs "audience-fit" → NEAR_DUPLICATE (not DUPLICATE) in dedupe
    with pytest.raises(DuplicateError):
        add_purpose(name="audience fit", method="Audience fit", force=False)
