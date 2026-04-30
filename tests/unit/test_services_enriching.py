"""Unit tests for TranscriptService.enrich_batch and SummaryService.enrich_batch."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.services.enriching.summary import SummaryService
from social_research_probe.services.enriching.transcript import TranscriptService


def _ok_result(service_name: str, output: object) -> ServiceResult:
    return ServiceResult(
        service_name=service_name,
        input_key="key",
        tech_results=[TechResult(tech_name="t", input="key", output=output, success=True)],
    )


def _fail_result(service_name: str) -> ServiceResult:
    return ServiceResult(
        service_name=service_name,
        input_key="key",
        tech_results=[TechResult(tech_name="t", input="key", output=None, success=False)],
    )


class TestTranscriptServiceEnrichBatch:
    @pytest.fixture()
    def svc(self):
        with patch.object(TranscriptService, "_get_technologies", return_value=[]):
            return TranscriptService()

    @pytest.mark.asyncio
    async def test_merges_transcript_when_success(self, svc):
        items = [{"url": "https://youtu.be/abc", "title": "Vid"}]
        results = [_ok_result(svc.service_name, "transcript text")]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out == [
            {"url": "https://youtu.be/abc", "title": "Vid", "transcript": "transcript text"}
        ]

    @pytest.mark.asyncio
    async def test_no_transcript_on_failure(self, svc):
        items = [{"url": "https://youtu.be/abc"}]
        results = [_fail_result(svc.service_name)]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out == [{"url": "https://youtu.be/abc"}]
        assert "transcript" not in out[0]

    @pytest.mark.asyncio
    async def test_skips_non_dict_items(self, svc):
        items = [{"url": "u"}, "not-a-dict"]
        results = [
            _ok_result(svc.service_name, "t1"),
            _ok_result(svc.service_name, "t2"),
        ]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert len(out) == 1
        assert out[0]["transcript"] == "t1"

    @pytest.mark.asyncio
    async def test_multiple_items_mixed(self, svc):
        items = [{"url": "u1"}, {"url": "u2"}]
        results = [_ok_result(svc.service_name, "tx1"), _fail_result(svc.service_name)]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out[0]["transcript"] == "tx1"
        assert "transcript" not in out[1]


class TestSummaryServiceEnrichBatch:
    @pytest.fixture()
    def svc(self):
        with patch.object(SummaryService, "_get_technologies", return_value=[]):
            return SummaryService()

    @pytest.mark.asyncio
    async def test_merges_summary_when_success(self, svc):
        items = [{"title": "T", "transcript": "text"}]
        results = [_ok_result(svc.service_name, "short summary")]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out[0]["summary"] == "short summary"
        assert out[0]["one_line_takeaway"] == "short summary"

    @pytest.mark.asyncio
    async def test_no_summary_on_failure(self, svc):
        items = [{"title": "T"}]
        results = [_fail_result(svc.service_name)]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out == [{"title": "T"}]
        assert "summary" not in out[0]
        assert "one_line_takeaway" not in out[0]

    @pytest.mark.asyncio
    async def test_multiple_items_mixed(self, svc):
        items = [{"title": "A"}, {"title": "B"}]
        results = [_ok_result(svc.service_name, "sum A"), _fail_result(svc.service_name)]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out[0]["summary"] == "sum A"
        assert out[0]["one_line_takeaway"] == "sum A"
        assert "summary" not in out[1]

    @pytest.mark.asyncio
    async def test_preserves_existing_fields(self, svc):
        items = [{"title": "T", "score": 42}]
        results = [_ok_result(svc.service_name, "the summary")]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out[0]["score"] == 42
        assert out[0]["summary"] == "the summary"
