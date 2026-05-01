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
        assert out[0]["transcript"] == "transcript text"
        assert out[0]["transcript_status"] == "available"

    @pytest.mark.asyncio
    async def test_no_transcript_on_failure(self, svc):
        items = [{"url": "https://youtu.be/abc"}]
        results = [_fail_result(svc.service_name)]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert "transcript" not in out[0]
        assert out[0]["transcript_status"] == "unavailable"

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
        assert out[0]["transcript_status"] == "available"
        assert "transcript" not in out[1]
        assert out[1]["transcript_status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_failed_status_when_tech_has_error(self, svc):
        items = [{"url": "u1"}]
        error_result = ServiceResult(
            service_name=svc.service_name,
            input_key="key",
            tech_results=[
                TechResult(
                    tech_name="t", input="key", output=None, success=False, error="API error"
                )
            ],
        )
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=[error_result])):
            out = await svc.enrich_batch(items)
        assert out[0]["transcript_status"] == "failed"
        assert "transcript" not in out[0]


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

    @pytest.mark.asyncio
    async def test_sets_summary_source_from_surrogate(self, svc):
        items = [
            {
                "title": "T",
                "text_surrogate": {"primary_text_source": "description"},
            }
        ]
        results = [_ok_result(svc.service_name, "desc summary")]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert out[0]["summary_source"] == "description"

    @pytest.mark.asyncio
    async def test_no_summary_source_without_surrogate(self, svc):
        items = [{"title": "T"}]
        results = [_ok_result(svc.service_name, "plain summary")]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert "summary_source" not in out[0]

    @pytest.mark.asyncio
    async def test_no_summary_source_on_failure(self, svc):
        items = [{"title": "T", "text_surrogate": {"primary_text_source": "transcript"}}]
        results = [_fail_result(svc.service_name)]
        with patch.object(svc, "execute_batch", new=AsyncMock(return_value=results)):
            out = await svc.enrich_batch(items)
        assert "summary_source" not in out[0]


class TestSummaryEnsembleTechSurrogate:
    @pytest.mark.asyncio
    async def test_uses_surrogate_primary_text(self):
        from social_research_probe.technologies.enriching import SummaryEnsembleTech

        tech = SummaryEnsembleTech()
        captured = {}

        async def fake_llm(prompt):
            captured["prompt"] = prompt
            return "summary"

        data = {
            "title": "Video Title",
            "transcript": "original transcript",
            "text_surrogate": {"primary_text": "description fallback text"},
        }
        with patch("social_research_probe.utils.llm.ensemble.multi_llm_prompt", fake_llm):
            result = await tech._execute(data)
        assert result == "summary"
        assert "Content:" in captured["prompt"]
        assert "description fallback text" in captured["prompt"]
        assert "original transcript" not in captured["prompt"]

    @pytest.mark.asyncio
    async def test_falls_back_to_transcript_without_surrogate(self):
        from social_research_probe.technologies.enriching import SummaryEnsembleTech

        tech = SummaryEnsembleTech()
        captured = {}

        async def fake_llm(prompt):
            captured["prompt"] = prompt
            return "summary"

        data = {"title": "T", "transcript": "raw transcript text"}
        with patch("social_research_probe.utils.llm.ensemble.multi_llm_prompt", fake_llm):
            await tech._execute(data)
        assert "Transcript:" in captured["prompt"]
        assert "raw transcript text" in captured["prompt"]
