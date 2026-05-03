"""Unit tests for YouTubeClaimsStage and claim-aware CorroborationHostTech."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import social_research_probe.platforms.youtube as yt
from social_research_probe.platforms.state import PipelineState
from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.technologies.corroborates import CorroborationHostTech


@pytest.fixture
def enabled_state(monkeypatch):
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.service_enabled.return_value = True
    cfg.technology_enabled.return_value = True
    cfg.raw = {"corroboration": {"max_claims_per_item": 5}}
    monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
    cmd = MagicMock()
    cmd.platform = "youtube"
    return PipelineState(
        platform_type="youtube",
        cmd=cmd,
        cache=None,
        platform_config={"enrich_top_n": 2},
        inputs={"topic": "ai"},
    )


def _mk_service_result(output: object, success: bool = True) -> ServiceResult:
    return ServiceResult(
        service_name="youtube.enriching.claims",
        input_key="",
        tech_results=[
            TechResult(tech_name="claim_extractor", input={}, output=output, success=success)
        ],
    )


def _sample_claim(needs_corroboration: bool = True) -> dict:
    return {
        "claim_id": "abc123abc123abcd",
        "claim_text": "AI will replace 50% of jobs.",
        "evidence_text": "AI will replace 50% of jobs.",
        "claim_type": "prediction",
        "source_url": "https://youtube.com/watch?v=vid1",
        "needs_corroboration": needs_corroboration,
        "corroboration_status": "pending",
    }


class TestYouTubeClaimsStageName:
    def test_stage_name(self) -> None:
        assert yt.YouTubeClaimsStage().stage_name == "claims"

    def test_claims_stage_before_corroborate_in_pipeline(self) -> None:
        flat = [type(s).__name__ for g in yt.YouTubePipeline().stages() for s in g]
        assert flat.index("YouTubeClaimsStage") < flat.index("YouTubeCorroborateStage")


class TestYouTubeClaimsStageDisabled:
    def test_disabled_writes_passthrough(self, enabled_state) -> None:
        enabled_state.set_stage_output("summary", {"top_n": [{"id": "1"}]})
        stage = yt.YouTubeClaimsStage()
        with patch.object(stage, "_is_enabled", return_value=False):
            out = asyncio.run(stage.execute(enabled_state))
        assert out.get_stage_output("claims")["top_n"] == [{"id": "1"}]

    def test_empty_top_n_writes_empty_claims(self, enabled_state) -> None:
        enabled_state.set_stage_output("summary", {"top_n": []})
        out = asyncio.run(yt.YouTubeClaimsStage().execute(enabled_state))
        assert out.get_stage_output("claims") == {"top_n": []}


class TestYouTubeClaimsStageEnabled:
    def test_merges_extracted_claims_into_items(self, enabled_state, monkeypatch) -> None:
        item = {"id": "vid1", "title": "T"}
        claims = [_sample_claim()]
        merged = {**item, "extracted_claims": claims}
        enabled_state.set_stage_output("summary", {"top_n": [item]})

        async def fake_one(self, data):
            return _mk_service_result(merged)

        monkeypatch.setattr(
            "social_research_probe.services.enriching.claims.ClaimExtractionService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeClaimsStage().execute(enabled_state))
        result_items = out.get_stage_output("claims")["top_n"]
        assert result_items[0]["extracted_claims"] == claims

    def test_non_dict_item_passed_through_unchanged(self, enabled_state, monkeypatch) -> None:
        enabled_state.set_stage_output("summary", {"top_n": ["not-a-dict"]})

        async def fail(self, data):
            raise AssertionError("service must not be called for non-dict item")

        monkeypatch.setattr(
            "social_research_probe.services.enriching.claims.ClaimExtractionService.execute_one",
            fail,
        )
        out = asyncio.run(yt.YouTubeClaimsStage().execute(enabled_state))
        assert out.get_stage_output("claims")["top_n"] == ["not-a-dict"]

    def test_service_failure_preserves_item_without_claims(
        self, enabled_state, monkeypatch
    ) -> None:
        item = {"id": "vid1", "title": "T"}
        enabled_state.set_stage_output("summary", {"top_n": [item]})

        async def fake_one(self, data):
            return _mk_service_result(None, success=False)

        monkeypatch.setattr(
            "social_research_probe.services.enriching.claims.ClaimExtractionService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeClaimsStage().execute(enabled_state))
        result_items = out.get_stage_output("claims")["top_n"]
        assert result_items[0] == {**item, "extracted_claims": []}

    def test_writes_to_claims_output_key(self, enabled_state, monkeypatch) -> None:
        item = {"id": "vid1"}
        enabled_state.set_stage_output("summary", {"top_n": [item]})

        async def fake_one(self, data):
            return _mk_service_result({**item, "extracted_claims": []})

        monkeypatch.setattr(
            "social_research_probe.services.enriching.claims.ClaimExtractionService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeClaimsStage().execute(enabled_state))
        assert "top_n" in out.get_stage_output("claims")

    def test_corroborate_stage_reads_from_claims(self, enabled_state, monkeypatch) -> None:
        enabled_state.set_stage_output("claims", {"top_n": [{"id": "1"}]})
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.corroborate.CorroborationService.__init__",
            lambda self: setattr(self, "providers", []) or None,
        )
        out = asyncio.run(yt.YouTubeCorroborateStage().execute(enabled_state))
        assert out.get_stage_output("corroborate")["top_n"] == [{"id": "1"}]


class TestCorroborationHostTechFallback:
    def test_non_dict_input_falls_back_to_title(self, monkeypatch) -> None:
        async def fake_corroborate(claim, providers):
            return {
                "claim_text": claim.text,
                "results": [],
                "aggregate_verdict": "inconclusive",
                "aggregate_confidence": 0.0,
            }

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            fake_corroborate,
        )
        result = asyncio.run(CorroborationHostTech([])._execute("raw string"))
        assert result["claim_text"] == "raw string"

    def test_no_extracted_claims_falls_back_to_title(self, monkeypatch) -> None:
        async def fake_corroborate(claim, providers):
            return {
                "claim_text": claim.text,
                "results": [],
                "aggregate_verdict": "inconclusive",
                "aggregate_confidence": 0.0,
            }

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            fake_corroborate,
        )
        result = asyncio.run(CorroborationHostTech([])._execute({"title": "my title", "url": "u"}))
        assert result["claim_text"] == "my title"

    def test_no_corroborable_claims_falls_back_to_title(self, monkeypatch) -> None:
        async def fake_corroborate(claim, providers):
            return {
                "claim_text": claim.text,
                "results": [],
                "aggregate_verdict": "inconclusive",
                "aggregate_confidence": 0.0,
            }

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            fake_corroborate,
        )
        data = {"title": "my title", "extracted_claims": [_sample_claim(needs_corroboration=False)]}
        result = asyncio.run(CorroborationHostTech([])._execute(data))
        assert result["claim_text"] == "my title"


class TestCorroborationHostTechClaimAware:
    def _fake_corroborate(self, verdict: str = "supported"):
        async def _impl(claim, providers):
            return {
                "claim_text": claim.text,
                "results": [],
                "aggregate_verdict": verdict,
                "aggregate_confidence": 0.9,
            }

        return _impl

    def test_claim_aware_path_updates_corroboration_status(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            self._fake_corroborate("supported"),
        )
        claim = _sample_claim()
        data = {"title": "T", "extracted_claims": [claim]}
        asyncio.run(CorroborationHostTech([])._execute(data))
        assert claim["corroboration_status"] == "supported"

    def test_claim_aware_path_returns_aggregate_verdict(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            self._fake_corroborate("refuted"),
        )
        data = {"title": "T", "extracted_claims": [_sample_claim()]}
        result = asyncio.run(CorroborationHostTech([])._execute(data))
        assert result["aggregate_verdict"] == "refuted"

    def test_limit_enforced_by_max_claims_per_item(self, monkeypatch) -> None:
        called: list[str] = []

        async def counting_corroborate(claim, providers):
            called.append(claim.text)
            return {
                "claim_text": claim.text,
                "results": [],
                "aggregate_verdict": "inconclusive",
                "aggregate_confidence": 0.0,
            }

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            counting_corroborate,
        )
        cfg = MagicMock()
        cfg.raw = {"corroboration": {"max_claims_per_item": 2}}
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda: cfg)
        claims = [{**_sample_claim(), "claim_text": f"Claim {i}."} for i in range(6)]
        data = {"title": "T", "extracted_claims": claims}
        asyncio.run(CorroborationHostTech([])._execute(data))
        assert len(called) == 2

    def test_all_claims_fail_gives_inconclusive(self, monkeypatch) -> None:
        async def always_fail(claim, providers):
            raise RuntimeError("all down")

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            always_fail,
        )
        data = {"title": "T", "extracted_claims": [_sample_claim()]}
        result = asyncio.run(CorroborationHostTech([])._execute(data))
        assert result["aggregate_verdict"] == "inconclusive"
        assert result["aggregate_confidence"] == 0.0

    def test_tie_verdict_resolves_to_inconclusive(self, monkeypatch) -> None:
        verdicts = iter(["supported", "refuted"])

        async def alternating(claim, providers):
            v = next(verdicts)
            return {
                "claim_text": claim.text,
                "results": [],
                "aggregate_verdict": v,
                "aggregate_confidence": 0.9,
            }

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            alternating,
        )
        claims = [_sample_claim(), {**_sample_claim(), "claim_text": "Revenue grew 42%."}]
        data = {"title": "T", "extracted_claims": claims}
        result = asyncio.run(CorroborationHostTech([])._execute(data))
        assert result["aggregate_verdict"] == "inconclusive"

    def test_per_claim_failure_is_non_fatal(self, monkeypatch) -> None:
        call_count = 0

        async def failing_corroborate(claim, providers):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("provider down")
            return {
                "claim_text": claim.text,
                "results": [],
                "aggregate_verdict": "supported",
                "aggregate_confidence": 0.9,
            }

        monkeypatch.setattr(
            "social_research_probe.technologies.corroborates.corroborate_claim",
            failing_corroborate,
        )
        claims = [_sample_claim(), {**_sample_claim(), "claim_text": "Revenue grew 42%."}]
        data = {"title": "T", "extracted_claims": claims}
        result = asyncio.run(CorroborationHostTech([])._execute(data))
        assert result["aggregate_verdict"] == "supported"
        assert len(result["results"]) == 1
