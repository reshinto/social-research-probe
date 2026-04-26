"""Tests for summary enrichment service caching."""

from __future__ import annotations

import json

import pytest

from social_research_probe.services.enriching.summary import SummaryService


@pytest.mark.asyncio
async def test_summary_service_uses_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    calls = 0

    async def fake_multi_llm_prompt(prompt: str) -> str:
        nonlocal calls
        calls += 1
        return f"summary for {prompt[:10]}"

    monkeypatch.setattr(
        "social_research_probe.services.llm.ensemble.multi_llm_prompt",
        fake_multi_llm_prompt,
    )

    item = {
        "url": "https://www.youtube.com/watch?v=abc12345678",
        "title": "Title",
        "transcript": "Transcript body",
    }
    first = await SummaryService().execute_one(item)
    second = await SummaryService().execute_one(item)

    assert calls == 1
    assert first.tech_results[0].output == second.tech_results[0].output
    cache_files = list((tmp_path / "cache" / "summaries").glob("*.json"))
    assert cache_files
    payload = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert list(payload.values()) == [first.tech_results[0].output]
    assert next(iter(payload)).startswith("Summarise this YouTube video")
