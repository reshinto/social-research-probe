"""Topics CRUD with dedupe + atomic writes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from social_research_probe.errors import DuplicateError, SrpError

from social_research_probe.utils.command_models.topics import (
    add_topics,
    remove_topics,
    rename_topic,
    show_topics,
)


def _read(data_dir: Path) -> dict:
    return json.loads((data_dir / "topics.json").read_text())


def test_add_new_topics(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents", "robotics"], force=False)
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents", "robotics"]


def test_add_keeps_alphabetical_order(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["robotics"], force=False)
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents", "robotics"]


def test_add_exact_duplicate_exits_3(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    with pytest.raises(DuplicateError):
        add_topics(tmp_data_dir, ["ai agents"], force=False)


def test_add_near_duplicate_exits_3(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    with pytest.raises(DuplicateError):
        add_topics(tmp_data_dir, ["ai agent"], force=False)


def test_add_with_force_overrides(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    add_topics(tmp_data_dir, ["ai agent"], force=True)
    state = _read(tmp_data_dir)
    assert "ai agent" in state["topics"]
    assert "ai agents" in state["topics"]


def test_remove_existing(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents", "robotics"], force=False)
    remove_topics(tmp_data_dir, ["robotics"])
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents"]


def test_remove_missing_is_noop(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    remove_topics(tmp_data_dir, ["nonexistent"])
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents"]


def test_rename(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    rename_topic(tmp_data_dir, "ai agents", "autonomous agents")
    state = _read(tmp_data_dir)
    assert state["topics"] == ["autonomous agents"]


def test_show_returns_list(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    assert show_topics(tmp_data_dir) == ["ai agents"]


def test_rename_onto_existing_raises(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents", "robotics"], force=False)
    with pytest.raises(DuplicateError):
        rename_topic(tmp_data_dir, "robotics", "ai agents")


def test_rename_nonexistent_old_raises(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    with pytest.raises(SrpError):
        rename_topic(tmp_data_dir, "nonexistent", "something new")


def test_save_with_duplicates_raises(tmp_data_dir: Path):
    """Line 27: _save raises DuplicateError if topics list has internal duplicates."""
    from social_research_probe.utils.command_models.topics import _save

    data = {"schema_version": 1, "topics": ["ai", "ai"]}
    with pytest.raises(DuplicateError, match="internal error"):
        _save(tmp_data_dir, data)


def test_add_topics_dedupes_within_values(tmp_data_dir: Path):
    """Branch 60->59: _save deduplication loop skips already-seen values (v IS in seen)."""
    # With force=True, duplicate values within the input list are allowed in to_add
    # The dedup loop at line 59-62 filters them out
    add_topics(tmp_data_dir, ["ai agents", "ai agents"], force=True)
    state = _read(tmp_data_dir)
    assert state["topics"].count("ai agents") == 1
