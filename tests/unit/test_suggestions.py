"""Rule-based topic/purpose suggestions + pending staging."""
from __future__ import annotations

import json

import pytest
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





import pytest


def test_suggest_topics_breaks_at_count(tmp_data_dir):
    """Lines 62->67, 65->62: suggest_topics stops early when count is reached."""
    drafts = suggest_topics(tmp_data_dir, count=1)
    assert len(drafts) == 1


def test_suggest_purposes_breaks_at_count(tmp_data_dir):
    """Lines 75->80, 78->75: suggest_purposes stops early when count is reached."""
    drafts = suggest_purposes(tmp_data_dir, count=1)
    assert len(drafts) == 1


def test_stage_suggestions_missing_value_raises(tmp_data_dir):
    """Line 99: topic candidate without value raises ValidationError."""
    from social_research_probe.errors import ValidationError
    with pytest.raises(ValidationError, match="missing .value."):
        stage_suggestions(
            tmp_data_dir,
            topic_candidates=[{"reason": "gap"}],
            purpose_candidates=[],
        )


def test_stage_suggestions_missing_name_or_method_raises(tmp_data_dir):
    """Line 114: purpose candidate without name/method raises ValidationError."""
    from social_research_probe.errors import ValidationError
    with pytest.raises(ValidationError, match="missing name/method"):
        stage_suggestions(
            tmp_data_dir,
            topic_candidates=[],
            purpose_candidates=[{"evidence_priorities": []}],
        )


def test_apply_pending_duplicate_topic_stays_pending(tmp_data_dir):
    """Lines 156-157: DuplicateError on topic apply keeps it in pending."""
    add_topics(tmp_data_dir, ["x"], force=False)
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "x", "reason": "gap"}],
        purpose_candidates=[],
    )
    apply_pending(tmp_data_dir, topic_ids="all", purpose_ids="all")
    remaining = _pending(tmp_data_dir)["pending_topic_suggestions"]
    assert len(remaining) == 1


def test_apply_pending_duplicate_purpose_stays_pending(tmp_data_dir):
    """Lines 162-163: DuplicateError on purpose apply keeps it in pending."""
    add_purpose(tmp_data_dir, name="trends", method="Track trends", force=False)
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[],
        purpose_candidates=[{"name": "trends", "method": "Track trends", "evidence_priorities": []}],
    )
    apply_pending(tmp_data_dir, topic_ids="all", purpose_ids="all")
    remaining = _pending(tmp_data_dir)["pending_purpose_suggestions"]
    assert len(remaining) == 1


def test_suggest_topics_exhausts_pool(tmp_data_dir):
    """Branch 62->67: suggest_topics loop exhausts all pool candidates (count > pool size)."""
    drafts = suggest_topics(tmp_data_dir, count=999)
    # Should return all unique candidates from the pool, not 999
    assert len(drafts) <= 8  # pool has 8 entries
    assert len(drafts) > 0


def test_suggest_topics_skips_non_new(tmp_data_dir):
    """Branch 65->62: suggest_topics skips candidates that are duplicates."""
    # Add all seed pool topics to existing so classify returns non-NEW for all
    from social_research_probe.commands.suggestions import _TOPIC_SEED_POOL
    add_topics(tmp_data_dir, list(_TOPIC_SEED_POOL), force=True)
    drafts = suggest_topics(tmp_data_dir, count=5)
    assert drafts == []


def test_suggest_purposes_exhausts_pool(tmp_data_dir):
    """Branch 75->80: suggest_purposes loop exhausts all pool candidates."""
    drafts = suggest_purposes(tmp_data_dir, count=999)
    from social_research_probe.commands.suggestions import _PURPOSE_SEED_POOL
    assert len(drafts) <= len(_PURPOSE_SEED_POOL)
    assert len(drafts) > 0


def test_suggest_purposes_skips_non_new(tmp_data_dir):
    """Branch 78->75: suggest_purposes skips candidates that are duplicates."""
    from social_research_probe.commands.suggestions import _PURPOSE_SEED_POOL
    for name, method in _PURPOSE_SEED_POOL:
        add_purpose(tmp_data_dir, name=name, method=method, force=False)
    drafts = suggest_purposes(tmp_data_dir, count=5)
    assert drafts == []
