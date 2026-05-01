"""Tests for TextSurrogateService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from social_research_probe.services.enriching.text_surrogate import TextSurrogateService


class TestFromItemBasic:
    def test_empty_dict(self):
        s = TextSurrogateService.from_item({})
        assert s["evidence_tier"] == "metadata_only"
        assert s["primary_text"] == ""
        assert s["primary_text_source"] == "title"
        assert s["char_count"] == 0
        assert s["evidence_layers"] == []
        assert s["transcript_status"] == "not_attempted"

    def test_title_only(self):
        s = TextSurrogateService.from_item({"title": "My Video"})
        assert s["primary_text"] == "My Video"
        assert s["primary_text_source"] == "title"
        assert s["evidence_tier"] == "metadata_only"
        assert s["evidence_layers"] == ["title"]

    def test_with_description(self):
        s = TextSurrogateService.from_item(
            {
                "title": "My Video",
                "text_excerpt": "A longer description of the video.",
            }
        )
        assert s["primary_text"] == "A longer description of the video."
        assert s["primary_text_source"] == "description"
        assert s["description"] == "A longer description of the video."
        assert s["evidence_layers"] == ["title", "description"]
        assert s["evidence_tier"] == "metadata_only"

    def test_description_key_fallback(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "description": "From description key",
            }
        )
        assert s["description"] == "From description key"
        assert s["primary_text_source"] == "description"

    def test_text_excerpt_preferred_over_description_key(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "text_excerpt": "From excerpt",
                "description": "From desc key",
            }
        )
        assert s["description"] == "From excerpt"

    def test_with_transcript(self):
        s = TextSurrogateService.from_item(
            {
                "title": "My Video",
                "transcript": "Full transcript text here",
            }
        )
        assert s["primary_text"] == "Full transcript text here"
        assert s["primary_text_source"] == "transcript"
        assert s["evidence_tier"] == "metadata_transcript"
        assert "transcript" in s["evidence_layers"]

    def test_empty_transcript_treated_as_absent(self):
        s = TextSurrogateService.from_item(
            {
                "title": "My Video",
                "text_excerpt": "Description",
                "transcript": "",
            }
        )
        assert s["primary_text"] == "Description"
        assert s["primary_text_source"] == "description"
        assert "transcript" not in s["evidence_layers"]
        assert s["evidence_tier"] == "metadata_only"


class TestFromItemComments:
    def test_with_comments(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "comments": ["great video", "thanks"],
            }
        )
        assert s["evidence_tier"] == "metadata_comments"
        assert "comments" in s["evidence_layers"]

    def test_empty_comments_treated_as_absent(self):
        s = TextSurrogateService.from_item({"title": "V", "comments": []})
        assert "comments" not in s["evidence_layers"]
        assert s["evidence_tier"] == "metadata_only"

    def test_with_transcript_and_comments(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "transcript": "text",
                "comments": ["c1"],
            }
        )
        assert s["evidence_tier"] == "metadata_comments_transcript"


class TestFromItemExternalSnippets:
    def test_with_external_snippets(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "external_snippets": ["snippet from reuters"],
            }
        )
        assert s["evidence_tier"] == "metadata_external"
        assert "external_snippets" in s["evidence_layers"]

    def test_empty_external_treated_as_absent(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "external_snippets": [],
            }
        )
        assert "external_snippets" not in s["evidence_layers"]


class TestFromItemFull:
    def test_full_tier(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "transcript": "t",
                "comments": ["c"],
                "external_snippets": ["e"],
            }
        )
        assert s["evidence_tier"] == "full"


class TestFromItemTranscriptStatus:
    def test_carries_transcript_status(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "transcript_status": "available",
            }
        )
        assert s["transcript_status"] == "available"

    def test_default_not_attempted(self):
        s = TextSurrogateService.from_item({"title": "V"})
        assert s["transcript_status"] == "not_attempted"


class TestFromItemConfidencePenalties:
    def test_no_transcript_penalty(self):
        s = TextSurrogateService.from_item({"title": "V"})
        assert "no_transcript" in s["confidence_penalties"]

    def test_no_description_penalty(self):
        s = TextSurrogateService.from_item({"title": "V"})
        assert "no_description" in s["confidence_penalties"]

    def test_no_penalties_when_all_present(self):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "text_excerpt": "desc",
                "transcript": "text",
            }
        )
        assert s["confidence_penalties"] == []


class TestFromItemWarnings:
    @pytest.mark.parametrize("status", ["failed", "timeout", "provider_blocked"])
    def test_warning_on_bad_status(self, status):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "transcript_status": status,
            }
        )
        assert s["warnings"] == [f"transcript_{status}"]

    @pytest.mark.parametrize("status", ["not_attempted", "available", "unavailable", "disabled"])
    def test_no_warning_on_normal_status(self, status):
        s = TextSurrogateService.from_item(
            {
                "title": "V",
                "transcript_status": status,
            }
        )
        assert s["warnings"] == []


class TestFromItemCharCount:
    def test_matches_primary_text_length(self):
        s = TextSurrogateService.from_item({"title": "Hello World"})
        assert s["char_count"] == len("Hello World")

    def test_zero_for_empty(self):
        s = TextSurrogateService.from_item({})
        assert s["char_count"] == 0


class TestFromItemPlatformDetection:
    def test_youtube_com(self):
        s = TextSurrogateService.from_item({"url": "https://www.youtube.com/watch?v=abc"})
        assert s["platform"] == "youtube"

    def test_youtu_be(self):
        s = TextSurrogateService.from_item({"url": "https://youtu.be/abc"})
        assert s["platform"] == "youtube"

    def test_unknown_domain(self):
        s = TextSurrogateService.from_item({"url": "https://example.com/page"})
        assert s["platform"] == ""

    def test_empty_url(self):
        s = TextSurrogateService.from_item({})
        assert s["platform"] == ""


class TestFromItemPublishedAt:
    def test_datetime_coercion(self):
        dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        s = TextSurrogateService.from_item({"published_at": dt})
        assert s["published_at"] == "2026-01-15T12:00:00+00:00"

    def test_string_passthrough(self):
        s = TextSurrogateService.from_item({"published_at": "2026-01-15"})
        assert s["published_at"] == "2026-01-15"

    def test_none_becomes_empty(self):
        s = TextSurrogateService.from_item({})
        assert s["published_at"] == ""

    def test_non_string_non_datetime(self):
        s = TextSurrogateService.from_item({"published_at": 12345})
        assert s["published_at"] == ""


class TestFromItemMetadata:
    def test_source_id(self):
        s = TextSurrogateService.from_item({"id": "abc123"})
        assert s["source_id"] == "abc123"

    def test_channel_from_channel_key(self):
        s = TextSurrogateService.from_item({"channel": "TestChannel"})
        assert s["channel_or_author"] == "TestChannel"

    def test_channel_fallback_to_author_name(self):
        s = TextSurrogateService.from_item({"author_name": "Author"})
        assert s["channel_or_author"] == "Author"


class TestTierFromLayers:
    @pytest.mark.parametrize(
        "layers, expected",
        [
            ([], "metadata_only"),
            (["title"], "metadata_only"),
            (["title", "description"], "metadata_only"),
            (["title", "comments"], "metadata_comments"),
            (["title", "transcript"], "metadata_transcript"),
            (["title", "description", "transcript"], "metadata_transcript"),
            (["title", "transcript", "comments"], "metadata_comments_transcript"),
            (["title", "description", "transcript", "comments"], "metadata_comments_transcript"),
            (["title", "external_snippets"], "metadata_external"),
            (["title", "transcript", "comments", "external_snippets"], "full"),
        ],
    )
    def test_tier_computation(self, layers, expected):
        assert TextSurrogateService.tier_from_layers(layers) == expected
