"""Tests for platforms/youtube/trust_hints.py."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from social_research_probe.platforms.youtube.trust_hints import account_age_days, citation_markers


def test_account_age_days_none_input():
    assert account_age_days(None) is None


def test_account_age_days_valid_iso():
    # A date 10 days ago should return approximately 10
    recent = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    result = account_age_days(recent)
    assert result is not None
    assert 9 <= result <= 11


def test_account_age_days_z_suffix():
    # "Z" suffix must be handled (replaced with +00:00 for fromisoformat)
    # Use a date 5 days ago in Z format
    recent_z = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = account_age_days(recent_z)
    assert result is not None
    assert 4 <= result <= 6


def test_citation_markers_empty():
    assert citation_markers(None) == []
    assert citation_markers("") == []


def test_citation_markers_with_urls():
    desc = "Check https://example.com and http://other.org for more info."
    result = citation_markers(desc)
    assert "https://example.com" in result
    assert "http://other.org" in result


def test_citation_markers_no_urls():
    result = citation_markers("Plain text with no URLs here")
    assert result == []
