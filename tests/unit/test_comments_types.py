"""Tests for Phase 2 comment-related types."""

from __future__ import annotations

import json

from social_research_probe.utils.core.types import (
    CommentsConfig,
    CommentsStatus,
    EvidenceTier,
    ScoredItem,
    SourceComment,
    TextSurrogate,
    TranscriptStatus,
)


def test_source_comment_all_fields():
    comment: SourceComment = {
        "source_id": "yt_abc123",
        "platform": "youtube",
        "comment_id": "Ugx1",
        "author": "Alice",
        "text": "Great video!",
        "like_count": 42,
        "published_at": "2026-01-01T00:00:00Z",
    }
    assert comment["comment_id"] == "Ugx1"
    assert comment["like_count"] == 42


def test_source_comment_json_serializable():
    comment: SourceComment = {
        "source_id": "yt_abc123",
        "platform": "youtube",
        "comment_id": "Ugx1",
        "author": "Alice",
        "text": "Great video!",
        "like_count": 5,
        "published_at": "2026-01-01T00:00:00Z",
    }
    serialized = json.dumps(comment)
    assert '"comment_id": "Ugx1"' in serialized


def test_comments_config_all_fields():
    cfg: CommentsConfig = {
        "enabled": True,
        "max_videos": 5,
        "max_comments_per_video": 20,
        "order": "relevance",
        "search_terms": ["AI", "safety"],
    }
    assert cfg["max_videos"] == 5
    assert cfg["search_terms"] == ["AI", "safety"]


def test_scored_item_accepts_comment_fields():
    item: ScoredItem = {
        "title": "Test",
        "comments_status": "available",
        "source_comments": [
            {
                "comment_id": "Ugx1",
                "author": "Bob",
                "text": "Nice",
                "like_count": 1,
                "published_at": "2026-01-01T00:00:00Z",
            }
        ],
        "comments": ["Nice"],
    }
    assert item["comments_status"] == "available"
    assert len(item["source_comments"]) == 1
    assert item["comments"] == ["Nice"]


def test_existing_types_import_cleanly():
    assert TranscriptStatus is not None
    assert EvidenceTier is not None
    assert TextSurrogate is not None
    assert CommentsStatus is not None
