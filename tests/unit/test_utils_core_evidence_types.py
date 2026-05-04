"""Tests for TranscriptStatus, EvidenceTier, TextSurrogate, and ScoredItem evidence fields."""

from __future__ import annotations

import json

from social_research_probe.utils.core.types import (
    EvidenceTier,
    ScoredItem,
    TextSurrogate,
    TranscriptStatus,
)


class TestTextSurrogateCreation:
    def test_minimal(self):
        s: TextSurrogate = {"primary_text": "hello"}
        assert s["primary_text"] == "hello"

    def test_all_fields(self):
        s: TextSurrogate = {
            "source_id": "abc123",
            "platform": "youtube",
            "url": "https://youtube.com/watch?v=abc",
            "title": "Test Video",
            "description": "A description",
            "channel_or_author": "TestChannel",
            "published_at": "2026-01-01T00:00:00Z",
            "comments": ["great video", "thanks"],
            "transcript": "full transcript text here",
            "transcript_status": "available",
            "external_snippets": ["snippet from reuters"],
            "primary_text": "full transcript text here",
            "primary_text_source": "transcript",
            "evidence_layers": ["title", "description", "transcript"],
            "evidence_tier": "metadata_transcript",
            "confidence_penalties": [],
            "warnings": [],
            "char_count": 25,
        }
        assert s["source_id"] == "abc123"
        assert s["evidence_tier"] == "metadata_transcript"
        assert len(s["evidence_layers"]) == 3

    def test_json_serializable(self):
        s: TextSurrogate = {
            "primary_text": "text",
            "evidence_layers": ["title"],
            "evidence_tier": "metadata_only",
            "comments": [],
            "external_snippets": [],
            "confidence_penalties": ["no_transcript"],
            "warnings": [],
            "char_count": 4,
        }
        serialized = json.dumps(s)
        restored = json.loads(serialized)
        assert restored == s


class TestScoredItemWithEvidenceFields:
    def test_new_fields_coexist_with_existing(self):
        item: ScoredItem = {
            "title": "Test",
            "url": "https://example.com",
            "transcript": "some transcript",
            "transcript_status": "available",
            "evidence_tier": "metadata_transcript",
            "text_surrogate": {
                "primary_text": "some transcript",
                "primary_text_source": "transcript",
                "evidence_tier": "metadata_transcript",
            },
            "corroboration_verdict": "supported",
        }
        assert item["transcript_status"] == "available"
        assert item["evidence_tier"] == "metadata_transcript"
        assert item["text_surrogate"]["primary_text_source"] == "transcript"

    def test_without_new_fields(self):
        item: ScoredItem = {
            "title": "Test",
            "url": "https://example.com",
            "transcript": "text",
        }
        assert "transcript_status" not in item
        assert "evidence_tier" not in item
        assert "text_surrogate" not in item

    def test_json_roundtrip(self):
        item: ScoredItem = {
            "title": "Test",
            "transcript_status": "failed",
            "evidence_tier": "metadata_only",
            "text_surrogate": {
                "primary_text": "Test",
                "primary_text_source": "title",
                "evidence_tier": "metadata_only",
                "confidence_penalties": ["no_transcript"],
                "warnings": ["transcript_failed"],
                "char_count": 4,
            },
        }
        serialized = json.dumps(item)
        restored = json.loads(serialized)
        assert restored["transcript_status"] == "failed"
        assert restored["text_surrogate"]["warnings"] == ["transcript_failed"]


class TestTranscriptStatusValues:
    def test_all_valid_values_assignable(self):
        values: list[TranscriptStatus] = [
            "not_attempted",
            "available",
            "unavailable",
            "failed",
            "timeout",
            "provider_blocked",
            "disabled",
        ]
        for v in values:
            s: TextSurrogate = {"transcript_status": v, "primary_text": "x"}
            assert s["transcript_status"] == v


class TestEvidenceTierValues:
    def test_all_valid_values_assignable(self):
        values: list[EvidenceTier] = [
            "metadata_only",
            "metadata_comments",
            "metadata_transcript",
            "metadata_comments_transcript",
            "metadata_external",
            "full",
        ]
        for v in values:
            s: TextSurrogate = {"evidence_tier": v, "primary_text": "x"}
            assert s["evidence_tier"] == v
