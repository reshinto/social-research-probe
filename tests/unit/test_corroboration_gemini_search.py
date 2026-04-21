"""Tests for the GeminiSearchBackend corroboration backend."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import pytest

import social_research_probe.llm.gemini_cli as gc
from social_research_probe.corroboration.gemini_search import (
    GeminiSearchBackend,
    _classify_verdict,
    _top_source_urls,
)


@dataclass
class _Claim:
    text: str


@pytest.fixture(autouse=True)
def _reset_availability_cache():
    gc._AVAILABILITY_CACHE = None
    yield
    gc._AVAILABILITY_CACHE = None


def test_classify_verdict_supported():
    verdict, conf = _classify_verdict("The evidence strongly supports the claim.")
    assert verdict == "supported"
    assert conf > 0.5


def test_classify_verdict_refuted():
    verdict, conf = _classify_verdict("This claim is false and has been refuted.")
    assert verdict == "refuted"
    assert conf > 0.5


def test_classify_verdict_mixed_maps_to_inconclusive():
    verdict, conf = _classify_verdict("Some truth but partially misleading.")
    assert verdict == "inconclusive"
    assert conf == 0.5


def test_classify_verdict_unmatched_default_inconclusive():
    verdict, conf = _classify_verdict("The sky is blue and grass is green.")
    assert verdict == "inconclusive"
    assert conf == 0.3


def test_top_source_urls_skips_empties_and_caps():
    payload = {
        "answer": "x",
        "citations": [
            {"title": "a", "url": "https://1", "snippet": ""},
            {"title": "b", "url": "", "snippet": ""},
            {"title": "c", "url": "https://2", "snippet": ""},
            {"title": "d", "url": "https://3", "snippet": ""},
            {"title": "e", "url": "https://4", "snippet": ""},
        ],
    }
    assert _top_source_urls(payload, limit=3) == ["https://1", "https://2", "https://3"]


def test_health_check_reflects_binary_presence():
    backend = GeminiSearchBackend()
    with patch("social_research_probe.corroboration.gemini_search.shutil.which", return_value=None):
        assert backend.health_check() is False
    with patch(
        "social_research_probe.corroboration.gemini_search.shutil.which",
        return_value="/usr/bin/gemini",
    ):
        assert backend.health_check() is True


@pytest.mark.asyncio
async def test_corroborate_inconclusive_when_cli_missing():
    backend = GeminiSearchBackend()
    with patch("social_research_probe.llm.gemini_cli.shutil.which", return_value=None):
        result = await backend.corroborate(_Claim(text="ice is cold"))
    assert result.verdict == "inconclusive"
    assert result.confidence == 0.0
    assert result.sources == []
    assert result.backend_name == "gemini_search"


@pytest.mark.asyncio
async def test_corroborate_classifies_and_extracts_sources():
    fake_result = {
        "answer": "Multiple sources confirm and support the claim accurately.",
        "citations": [{"title": "T", "url": "https://a", "snippet": "s"}],
    }

    async def _fake_search(*_args, **_kwargs):
        return fake_result

    backend = GeminiSearchBackend()
    with patch(
        "social_research_probe.corroboration.gemini_search.gemini_search",
        side_effect=_fake_search,
    ):
        result = await backend.corroborate(_Claim(text="claim"))
    assert result.verdict == "supported"
    assert "https://a" in result.sources
