"""Tests for utils.core.strings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from social_research_probe.utils.core.strings import (
    account_age_days,
    citation_markers,
    normalize_whitespace,
)


class TestNormalizeWhitespace:
    def test_strips_collapses_and_lowercases(self):
        assert normalize_whitespace("  Hello   World  ") == "hello world"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""

    def test_single_word(self):
        assert normalize_whitespace("Foo") == "foo"


class TestAccountAgeDays:
    def test_none_returns_none(self):
        assert account_age_days(None) is None

    def test_empty_returns_none(self):
        assert account_age_days("") is None

    def test_z_suffix_parsed(self):
        ten_days_ago = (datetime.now(UTC) - timedelta(days=10)).isoformat().replace("+00:00", "Z")
        result = account_age_days(ten_days_ago)
        assert result is not None
        assert 9 <= result <= 11

    def test_isoformat_with_offset(self):
        recent = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        result = account_age_days(recent)
        assert result is not None
        assert 1 <= result <= 3


class TestCitationMarkers:
    def test_none_returns_empty(self):
        assert citation_markers(None) == []

    def test_empty_returns_empty(self):
        assert citation_markers("") == []

    def test_extracts_http_and_https(self):
        text = "see http://example.com and https://foo.bar/baz here"
        assert citation_markers(text) == ["http://example.com", "https://foo.bar/baz"]

    def test_no_urls(self):
        assert citation_markers("plain text without links") == []
