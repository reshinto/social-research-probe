"""Tests for the Gemini CLI google-search adapter."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import social_research_probe.llm.gemini_cli as gc
from social_research_probe.errors import AdapterError


@pytest.fixture(autouse=True)
def _reset_availability_cache():
    gc._AVAILABILITY_CACHE = None
    yield
    gc._AVAILABILITY_CACHE = None


@pytest.mark.asyncio
async def test_gemini_cli_available_false_when_binary_missing():
    with patch("social_research_probe.llm.gemini_cli.shutil.which", return_value=None):
        assert await gc.gemini_cli_available() is False


@pytest.mark.asyncio
async def test_gemini_cli_available_true_when_binary_present():
    with patch("social_research_probe.llm.gemini_cli.shutil.which", return_value="/usr/bin/gemini"):
        assert await gc.gemini_cli_available() is True


@pytest.mark.asyncio
async def test_gemini_cli_available_memoised():
    gc._AVAILABILITY_CACHE = True
    with patch("social_research_probe.llm.gemini_cli.shutil.which", return_value=None) as which:
        assert await gc.gemini_cli_available() is True
        which.assert_not_called()


def test_parse_search_stdout_extracts_answer_and_citations():
    payload = json.dumps(
        {
            "response": "The claim is supported by recent reports.",
            "grounding": [
                {"title": "T1", "url": "https://a", "snippet": "s1"},
                {"title": "T2", "url": "https://b", "snippet": "s2"},
            ],
        }
    )
    result = gc._parse_search_stdout(payload)
    assert "supported" in result["answer"]
    assert result["citations"][0]["url"] == "https://a"
    assert len(result["citations"]) == 2


def test_parse_search_stdout_missing_citations_returns_empty_list():
    payload = json.dumps({"response": "answer text"})
    result = gc._parse_search_stdout(payload)
    assert result["citations"] == []
    assert result["answer"] == "answer text"


def test_parse_search_stdout_strips_markdown_fence():
    fenced = json.dumps({"response": "```\nactual\n```"})
    result = gc._parse_search_stdout(fenced)
    assert "actual" in result["answer"]


@pytest.mark.asyncio
async def test_gemini_search_returns_none_when_cli_missing():
    with patch("social_research_probe.llm.gemini_cli.shutil.which", return_value=None):
        out = await gc.gemini_search("does it rain on mars?")
    assert out is None


@pytest.mark.asyncio
async def test_gemini_search_returns_none_on_subprocess_error():
    def _raise(_argv, **_):
        raise AdapterError("boom")

    with (
        patch("social_research_probe.llm.gemini_cli.shutil.which", return_value="/usr/bin/gemini"),
        patch("social_research_probe.llm.gemini_cli.sp_run", side_effect=_raise),
    ):
        out = await gc.gemini_search("x")
    assert out is None


@pytest.mark.asyncio
async def test_gemini_search_returns_none_on_bad_json():
    class _Fake:
        stdout = "not json"

    with (
        patch("social_research_probe.llm.gemini_cli.shutil.which", return_value="/usr/bin/gemini"),
        patch("social_research_probe.llm.gemini_cli.sp_run", return_value=_Fake()),
    ):
        out = await gc.gemini_search("x")
    assert out is None


@pytest.mark.asyncio
async def test_gemini_search_happy_path():
    class _Fake:
        stdout = json.dumps(
            {"response": "Yes, it supports the claim.", "grounding": [{"title": "T", "url": "u"}]}
        )

    with (
        patch("social_research_probe.llm.gemini_cli.shutil.which", return_value="/usr/bin/gemini"),
        patch("social_research_probe.llm.gemini_cli.sp_run", return_value=_Fake()),
    ):
        out = await gc.gemini_search("claim")
    assert out is not None
    assert "supports" in out["answer"]
    assert out["citations"][0]["url"] == "u"
