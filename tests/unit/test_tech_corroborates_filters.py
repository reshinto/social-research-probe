"""Tests for tech.corroborates._filters."""

from __future__ import annotations

from social_research_probe.technologies.corroborates import _filters


class TestHost:
    def test_empty(self):
        assert _filters._host("") is None

    def test_basic(self):
        assert _filters._host("https://Example.com/foo") == "example.com"

    def test_invalid_returns_none_or_empty(self):
        assert _filters._host("not a url") is None or _filters._host("not a url") == "not a url"


class TestIsVideoUrl:
    def test_youtube(self):
        assert _filters.is_video_url("https://youtube.com/watch?v=x")

    def test_youtu_be(self):
        assert _filters.is_video_url("https://youtu.be/x")

    def test_other(self):
        assert not _filters.is_video_url("https://wikipedia.org")

    def test_blank(self):
        assert not _filters.is_video_url("")


class TestIsSelfSource:
    def test_no_source(self):
        assert not _filters.is_self_source("https://x.com", None)

    def test_exact(self):
        assert _filters.is_self_source("https://x.com/y", "https://x.com/y")

    def test_same_host(self):
        assert _filters.is_self_source("https://example.com/a", "https://example.com/b")

    def test_different_host(self):
        assert not _filters.is_self_source("https://a.com", "https://b.com")


class TestFilterResults:
    def test_drops_self_source_and_video(self):
        items = [
            {"url": "https://example.com/a"},  # self
            {"url": "https://youtube.com/v"},  # video
            {"url": "https://other.com/page"},
            {"url": ""},
        ]
        kept, self_n, video_n = _filters.filter_results(items, "https://example.com/x")
        assert self_n == 1 and video_n == 1
        urls = [k.get("url") for k in kept]
        assert "https://other.com/page" in urls
        assert "" in urls

    def test_custom_url_key(self):
        items = [{"link": "https://other.com"}, {"link": "https://youtube.com/v"}]
        kept, _, video_n = _filters.filter_results(items, None, url_key="link")
        assert video_n == 1
        assert kept[0]["link"] == "https://other.com"
