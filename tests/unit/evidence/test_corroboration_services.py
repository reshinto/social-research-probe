"""Evidence tests — corroboration backends produce verdict-classified evidence.

Seven services are covered via recorded golden payloads played back through
``respx``: Brave / Exa / Tavily HTTP backends, the runner-agnostic LLM search
backend, the host aggregator, claim extraction, and the top-N pipeline.

Phase 0 already verified the source-quality filters (self + video-domain
exclusion). This phase verifies the *end-to-end* contract: given a realistic
API response, does the backend correctly classify the verdict, preserve
citations verbatim, and emit the documented ``CorroborationResult`` shape?

Evidence receipt (service / golden / expected / why):

| Service | Golden | Verdict | Sources | Why |
| --- | --- | --- | --- | --- |
| Brave supported | ``brave_supported.json`` | ``"supported"`` | 3 non-video URLs preserved | found>0 branch of _build_result |
| Exa contradicted | ``exa_contradicted.json`` | ``"supported"`` (backend only finds URLs) | 2 sources | backend classifies by URL count, verdict classifier in llm_search downstream |
| Tavily mixed | ``tavily_mixed.json`` | ``"supported"`` | 3 sources | same URL-count contract |
| LLM search supported | ``llm_search_citations.json`` | ``"supported"`` | 3 cited URLs | verdict classifier picks "supported" from answer text |
| Host aggregator — unanimous | 2 supported + 1 supported | ``"supported"``, confidence weighted | majority-verdict + confidence-weighted | host.aggregate_verdict |
| Host aggregator — tied | 1 supported + 1 refuted | ``"inconclusive"`` | tie-break rule | documented in host.py:29-65 |
| Claim extraction | transcript with 1 factual sentence | 1 claim | only numeric/proper-noun sentences pass | validation/claims.py:_is_candidate |
| Top-N pipeline | 5 ScoredItems + stub backend | 5 results | concurrency + per-item corroboration | pipeline/corroboration.py:_corroborate_top_n |
"""

from __future__ import annotations

import httpx
import pytest
import respx

from social_research_probe.corroboration.base import CorroborationResult
from social_research_probe.corroboration.brave import BraveBackend
from social_research_probe.corroboration.exa import ExaBackend
from social_research_probe.corroboration.host import aggregate_verdict
from social_research_probe.corroboration.tavily import TavilyBackend
from social_research_probe.validation.claims import Claim, extract_claims


def _claim(text: str = "test claim", source_url: str | None = None) -> Claim:
    return Claim(text=text, source_text=text, index=0, source_url=source_url)


# ---------------------------------------------------------------------------
# HTTP backend replays
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_brave_supported_response_produces_supported_verdict(monkeypatch, golden):
    """Golden: Brave returns 3 non-video URLs for a real claim → supported."""
    monkeypatch.setenv("SRP_BRAVE_API_KEY", "test-key")
    payload = golden("corroboration/brave_supported.json")
    with respx.mock:
        respx.get("https://api.search.brave.com/res/v1/web/search").mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await BraveBackend().corroborate(
            _claim("GPT-4 was released in March 2023", source_url=None)
        )
    assert result.verdict == "supported"
    assert len(result.sources) == 3
    # Confidence is min(1.0, len(sources) * 0.2) = 0.6 for 3 sources.
    assert result.confidence == pytest.approx(0.6)
    assert result.backend_name == "brave"


@pytest.mark.anyio
async def test_exa_contradicted_response_still_returns_urls_as_supported(monkeypatch, golden):
    """Backend classifies by URL count only — the LLM search verdict
    classifier (Phase 0.b) is what distinguishes contradicted from
    supported. This test proves the parser hands the right URLs upstream."""
    monkeypatch.setenv("SRP_EXA_API_KEY", "test-key")
    payload = golden("corroboration/exa_contradicted.json")
    with respx.mock:
        respx.post("https://api.exa.ai/search").mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await ExaBackend().corroborate(_claim("flat earth"))
    assert result.verdict == "supported"  # two URLs found
    assert "https://www.wikipedia.org/wiki/Flat_Earth" in result.sources
    assert "https://skepticalscience.com/flat-earth-debunked.htm" in result.sources


@pytest.mark.anyio
async def test_tavily_mixed_response_preserves_all_urls(monkeypatch, golden):
    monkeypatch.setenv("SRP_TAVILY_API_KEY", "test-key")
    payload = golden("corroboration/tavily_mixed.json")
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=payload),
        )
        result = await TavilyBackend().corroborate(_claim("UBI effectiveness"))
    assert result.verdict == "supported"
    assert len(result.sources) == 3
    assert result.backend_name == "tavily"


# ---------------------------------------------------------------------------
# LLM search backend (Phase 0.b) with a golden AgenticSearchResult
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_llm_search_backend_classifies_supported_and_preserves_citations(monkeypatch, golden):
    """Runner routing was already covered in test_llm_search_routing.py.
    Here we prove the *integration* against the golden citation payload."""
    from social_research_probe.corroboration.llm_search import LLMSearchBackend
    from social_research_probe.llm.types import AgenticSearchCitation, AgenticSearchResult

    payload = golden("corroboration/llm_search_citations.json")
    canned = AgenticSearchResult(
        answer=payload["answer"],
        citations=[
            AgenticSearchCitation(url=c["url"], title=c["title"]) for c in payload["citations"]
        ],
        runner_name="gemini",
    )

    class _StubRunner:
        name = "gemini"
        supports_agentic_search = True

        def health_check(self):
            return True

        async def agentic_search(self, query, *, max_results=5, timeout_s=60.0):
            return canned

    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.load_active_config",
        lambda: type("C", (), {"llm_runner": "gemini"})(),
    )
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.get_runner",
        lambda name: _StubRunner(),
    )

    result = await LLMSearchBackend().corroborate(_claim())
    assert result.verdict == "supported"
    assert result.sources == [c["url"] for c in payload["citations"]]


# ---------------------------------------------------------------------------
# Host aggregator — majority vote + confidence-weighted combine
# ---------------------------------------------------------------------------


def test_host_aggregate_unanimous_supported():
    """Three supported verdicts with confidences 0.6, 0.6, 0.8 → 'supported'.

    Confidence-weighted average per host.py:29-65 formula:
        sum(c * c) / sum(c) = (0.36+0.36+0.64) / 2.0 = 0.68.
    """
    results = [
        CorroborationResult(
            verdict="supported", confidence=0.6, reasoning="", sources=[], backend_name="a"
        ),
        CorroborationResult(
            verdict="supported", confidence=0.6, reasoning="", sources=[], backend_name="b"
        ),
        CorroborationResult(
            verdict="supported", confidence=0.8, reasoning="", sources=[], backend_name="c"
        ),
    ]
    verdict, confidence = aggregate_verdict(results)
    assert verdict == "supported"
    assert confidence == pytest.approx((0.36 + 0.36 + 0.64) / 2.0, abs=1e-9)


def test_host_aggregate_tied_verdicts_resolve_to_inconclusive():
    """Tied plurality (1 supported, 1 refuted) → 'inconclusive' per tie rule."""
    results = [
        CorroborationResult(
            verdict="supported", confidence=0.7, reasoning="", sources=[], backend_name="a"
        ),
        CorroborationResult(
            verdict="refuted", confidence=0.7, reasoning="", sources=[], backend_name="b"
        ),
    ]
    verdict, _ = aggregate_verdict(results)
    assert verdict == "inconclusive"


def test_host_aggregate_empty_list_returns_inconclusive():
    verdict, confidence = aggregate_verdict([])
    assert verdict == "inconclusive"
    assert confidence == 0.0


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------


def test_claim_extraction_keeps_only_factual_sentences():
    """'OpenAI raised $10B.' has a number → kept; 'The sky is blue.' → rejected."""
    transcript = "OpenAI raised $10B in 2023. The sky is blue."
    claims = extract_claims(transcript)
    assert len(claims) == 1
    assert "10B" in claims[0].text


def test_claim_extraction_preserves_source_url_from_caller():
    """When upstream (Phase 0.a) plumbs source_url, every claim stamps it."""
    claims = extract_claims(
        "GPT-4 was released in March 2023.",
        source_text="YouTube video transcript",
        source_url="https://youtube.com/watch?v=abc",
    )
    assert len(claims) == 1
    assert claims[0].source_url == "https://youtube.com/watch?v=abc"


# ---------------------------------------------------------------------------
# Top-N pipeline — concurrent corroboration across items
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_top_n_pipeline_runs_one_claim_per_item(monkeypatch):
    """Given 5 ScoredItems, the top-N orchestrator returns exactly 5 results."""
    from social_research_probe.pipeline import corroboration as pipe

    async def _fake_host(claim, backends):
        return {
            "claim_text": claim.text,
            "results": [],
            "aggregate_verdict": "supported",
            "aggregate_confidence": 0.75,
        }

    monkeypatch.setattr("social_research_probe.corroboration.host.corroborate_claim", _fake_host)

    items = [
        {"title": f"Item {i}", "url": f"https://example.com/{i}", "one_line_takeaway": f"t {i}"}
        for i in range(5)
    ]
    results = await pipe._corroborate_top_n(items, ["brave"])
    assert len(results) == 5
    assert all(r["aggregate_verdict"] == "supported" for r in results)
