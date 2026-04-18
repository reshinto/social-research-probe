"""Rule-based topic/purpose suggestions + pending staging."""
from __future__ import annotations

import json
from pathlib import Path

from social_research_probe.commands.purposes import add_purpose
from social_research_probe.commands.suggestions import (
    apply_pending,
    discard_pending,
    show_pending,
    stage_suggestions,
    suggest_purposes,
    suggest_topics,
)
from social_research_probe.commands.topics import add_topics


def _pending(data_dir: Path) -> dict:
    return json.loads((data_dir / "pending_suggestions.json").read_text())


def test_suggest_topics_emits_gap_candidates(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    drafts = suggest_topics(tmp_data_dir, count=3)
    assert len(drafts) <= 3
    for d in drafts:
        assert "value" in d
        assert "reason" in d
        assert d["reason"] == "gap"


def test_suggest_purposes_emits_gap_candidates(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    drafts = suggest_purposes(tmp_data_dir, count=3)
    assert len(drafts) <= 3
    for d in drafts:
        assert "name" in d
        assert "method" in d


def test_stage_suggestions_assigns_ids_and_dedupe(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[
            {"value": "on-device LLMs", "reason": "gap"},
            {"value": "ai agent", "reason": "gap"},  # near-dup of "ai agents"
        ],
        purpose_candidates=[],
    )
    state = _pending(tmp_data_dir)
    topics = state["pending_topic_suggestions"]
    assert len(topics) == 2
    assert topics[0]["id"] == 1
    assert topics[1]["id"] == 2
    new_entry = next(t for t in topics if t["value"] == "on-device LLMs")
    near_entry = next(t for t in topics if t["value"] == "ai agent")
    assert new_entry["duplicate_status"] == "new"
    assert near_entry["duplicate_status"] == "near-duplicate"
    assert "ai agents" in near_entry["matches"]


def test_show_pending(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "a", "reason": "gap"}],
        purpose_candidates=[],
    )
    result = show_pending(tmp_data_dir)
    assert len(result["pending_topic_suggestions"]) == 1
    assert len(result["pending_purpose_suggestions"]) == 0


def test_apply_pending_all(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "x", "reason": "gap"}],
        purpose_candidates=[{"name": "p", "method": "m", "evidence_priorities": []}],
    )
    apply_pending(tmp_data_dir, topic_ids="all", purpose_ids="all")
    topics = json.loads((tmp_data_dir / "topics.json").read_text())["topics"]
    purposes = json.loads((tmp_data_dir / "purposes.json").read_text())["purposes"]
    assert "x" in topics
    assert "p" in purposes
    assert _pending(tmp_data_dir)["pending_topic_suggestions"] == []
    assert _pending(tmp_data_dir)["pending_purpose_suggestions"] == []


def test_apply_pending_by_ids(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "x", "reason": "gap"}, {"value": "y", "reason": "gap"}],
        purpose_candidates=[],
    )
    apply_pending(tmp_data_dir, topic_ids=[1], purpose_ids="all")
    topics = json.loads((tmp_data_dir / "topics.json").read_text())["topics"]
    assert topics == ["x"]
    remaining = _pending(tmp_data_dir)["pending_topic_suggestions"]
    assert len(remaining) == 1
    assert remaining[0]["value"] == "y"


def test_discard_pending_removes_without_applying(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "x", "reason": "gap"}],
        purpose_candidates=[],
    )
    discard_pending(tmp_data_dir, topic_ids="all", purpose_ids="all")
    topics = json.loads((tmp_data_dir / "topics.json").read_text())["topics"]
    assert topics == []
    assert _pending(tmp_data_dir)["pending_topic_suggestions"] == []
