"""Unit tests for TranscriptService and SummaryService execute_service logic."""

from __future__ import annotations

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


class TestTranscriptServiceExecuteService:
    @pytest.fixture()
    def svc(self):
        return TranscriptService()

    @pytest.mark.asyncio
    async def test_merges_transcript_when_success(self, svc):
        item = {"url": "https://youtu.be/abc", "title": "Vid"}
        result = await svc.execute_service(item, _ok_result(svc.service_name, "transcript text"))
        out = result.tech_results[0].output
        assert out["transcript"] == "transcript text"
        assert out["transcript_status"] == "available"

    @pytest.mark.asyncio
    async def test_no_transcript_on_failure(self, svc):
        result = await svc.execute_service(
            {"url": "https://youtu.be/abc"}, _fail_result(svc.service_name)
        )
        out = result.tech_results[0].output
        assert "transcript" not in out
        assert out["transcript_status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_failed_status_when_tech_has_error(self, svc):
        error_result = ServiceResult(
            service_name=svc.service_name,
            input_key="key",
            tech_results=[
                TechResult(
                    tech_name="t", input="key", output=None, success=False, error="API error"
                )
            ],
        )
        result = await svc.execute_service({"url": "u1"}, error_result)
        out = result.tech_results[0].output
        assert out["transcript_status"] == "failed"
        assert "transcript" not in out

    @pytest.mark.asyncio
    async def test_fallback_execution_calls_techs(self, svc, monkeypatch):
        class DummyTech:
            def __init__(self, name, result, should_raise=False):
                self.name = name
                self.result = result
                self.should_raise = should_raise
                self.caller_service = ""

            async def execute(self, url):
                if self.should_raise:
                    raise RuntimeError("boom")
                return self.result

        tech1 = DummyTech("t1", None, should_raise=True)
        tech2 = DummyTech("t2", "success text")
        monkeypatch.setattr(svc, "_get_technologies", lambda: [tech1, tech2])

        result = await svc.execute_service(
            {"url": "u1"},
            ServiceResult(service_name=svc.service_name, input_key="key", tech_results=[]),
        )
        assert len(result.tech_results) == 2
        # Note: TranscriptService overrides tech_results[0] with the final combined output and success state.
        assert result.tech_results[0].success
        assert result.tech_results[0].error == "boom"
        assert result.tech_results[1].success
        assert result.tech_results[1].output == "success text"

        out = result.tech_results[0].output
        assert out["transcript"] == "success text"
        assert out["transcript_status"] == "available"

    @pytest.mark.asyncio
    async def test_fallback_execution_exhausts_all_failing(self, svc, monkeypatch):
        class DummyTech:
            def __init__(self, name):
                self.name = name
                self.caller_service = ""

            async def execute(self, url):
                return None

        monkeypatch.setattr(svc, "_get_technologies", lambda: [DummyTech("t1"), DummyTech("t2")])
        result = await svc.execute_service(
            {"url": "u1"},
            ServiceResult(service_name=svc.service_name, input_key="key", tech_results=[]),
        )
        assert len(result.tech_results) == 2
        # Because both failed, tech_results[0].success is overwritten to False
        # and output becomes {"url": "u1", "transcript_status": "unavailable"}
        assert not result.tech_results[0].success
        assert result.tech_results[0].output.get("transcript_status") == "unavailable"

    @pytest.mark.asyncio
    async def test_fallback_execution_no_technologies(self, svc, monkeypatch):
        monkeypatch.setattr(svc, "_get_technologies", lambda: [])
        result = await svc.execute_service(
            {"url": "u1"},
            ServiceResult(service_name=svc.service_name, input_key="key", tech_results=[]),
        )
        assert len(result.tech_results) == 0

    @pytest.mark.asyncio
    async def test_non_dict_data_skips_output_merge(self, svc):
        result = await svc.execute_service(
            "https://youtu.be/abc",
            ServiceResult(
                service_name=svc.service_name,
                input_key="key",
                tech_results=[TechResult(tech_name="t", input="key", output="text", success=True)],
            ),
        )
        assert result.input_key == "https://youtu.be/abc"


class TestSummaryServiceExecuteService:
    @pytest.fixture()
    def svc(self):
        return SummaryService()

    @pytest.mark.asyncio
    async def test_merges_summary_when_success(self, svc):
        item = {"title": "T", "transcript": "text"}
        result = await svc.execute_service(item, _ok_result(svc.service_name, "short summary"))
        out = result.tech_results[0].output
        assert out["summary"] == "short summary"
        assert out["one_line_takeaway"] == "short summary"

    @pytest.mark.asyncio
    async def test_no_summary_on_failure(self, svc):
        item = {"title": "T"}
        result = await svc.execute_service(item, _fail_result(svc.service_name))
        assert result.tech_results[0].output == {"title": "T"}

    @pytest.mark.asyncio
    async def test_preserves_existing_fields(self, svc):
        item = {"title": "T", "score": 42}
        result = await svc.execute_service(item, _ok_result(svc.service_name, "the summary"))
        out = result.tech_results[0].output
        assert out["score"] == 42
        assert out["summary"] == "the summary"

    @pytest.mark.asyncio
    async def test_sets_summary_source_from_surrogate(self, svc):
        item = {
            "title": "T",
            "text_surrogate": {"primary_text_source": "description"},
        }
        result = await svc.execute_service(item, _ok_result(svc.service_name, "desc summary"))
        assert result.tech_results[0].output["summary_source"] == "description"

    @pytest.mark.asyncio
    async def test_no_summary_source_without_surrogate(self, svc):
        result = await svc.execute_service(
            {"title": "T"}, _ok_result(svc.service_name, "plain summary")
        )
        assert "summary_source" not in result.tech_results[0].output

    @pytest.mark.asyncio
    async def test_no_summary_source_on_failure(self, svc):
        item = {"title": "T", "text_surrogate": {"primary_text_source": "transcript"}}
        result = await svc.execute_service(item, _fail_result(svc.service_name))
        assert "summary_source" not in result.tech_results[0].output

    @pytest.mark.asyncio
    async def test_non_dict_input_only_updates_input_key(self, svc):
        result = await svc.execute_service("raw", _ok_result(svc.service_name, "summary"))
        assert result.input_key == "'raw'"

    @pytest.mark.asyncio
    async def test_dict_input_with_empty_result_keeps_item(self, svc):
        result = await svc.execute_service(
            {"title": "T"},
            ServiceResult(service_name=svc.service_name, input_key="T", tech_results=[]),
        )
        assert result.input_key == "T"


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
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "social_research_probe.utils.llm.ensemble.multi_llm_prompt", fake_llm
            )
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
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "social_research_probe.utils.llm.ensemble.multi_llm_prompt", fake_llm
            )
            await tech._execute(data)
        assert "Transcript:" in captured["prompt"]
        assert "raw transcript text" in captured["prompt"]
