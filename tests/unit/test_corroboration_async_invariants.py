"""Async-contract invariants for corroboration backends.

Each test asserts a structural invariant the async corroboration
architecture depends on — every backend's ``corroborate`` is a coroutine
function, no backend uses blocking ``urllib.request``, etc. Pure
structural checks (inspect, source scan); no I/O or network.
"""

from __future__ import annotations

import inspect

# ---------------------------------------------------------------------------
# A2: Corroboration backends must have async corroborate
# ---------------------------------------------------------------------------


def test_base_abc_corroborate_is_abstract_coroutine_function():
    """CorroborationBackend.corroborate() must be an abstract async method."""
    from social_research_probe.corroboration.base import CorroborationBackend

    assert inspect.iscoroutinefunction(CorroborationBackend.corroborate)


def test_exa_corroborate_is_coroutine_function():
    """ExaBackend.corroborate() must be a coroutine function."""
    from social_research_probe.corroboration.exa import ExaBackend

    assert inspect.iscoroutinefunction(ExaBackend.corroborate)


def test_brave_corroborate_is_coroutine_function():
    """BraveBackend.corroborate() must be a coroutine function."""
    from social_research_probe.corroboration.brave import BraveBackend

    assert inspect.iscoroutinefunction(BraveBackend.corroborate)


def test_tavily_corroborate_is_coroutine_function():
    """TavilyBackend.corroborate() must be a coroutine function."""
    from social_research_probe.corroboration.tavily import TavilyBackend

    assert inspect.iscoroutinefunction(TavilyBackend.corroborate)


# ---------------------------------------------------------------------------
# A2: backends must use httpx, not urllib.request
# ---------------------------------------------------------------------------


def test_brave_does_not_use_urllib_request():
    """BraveBackend._search must use httpx, not urllib.request."""
    from social_research_probe.corroboration import brave

    assert "urllib.request" not in inspect.getsource(brave)


def test_exa_does_not_use_urllib_request():
    """ExaBackend._search must use httpx, not urllib.request."""
    from social_research_probe.corroboration import exa

    assert "urllib.request" not in inspect.getsource(exa)


def test_tavily_does_not_use_urllib_request():
    """TavilyBackend._search must use httpx, not urllib.request."""
    from social_research_probe.corroboration import tavily

    assert "urllib.request" not in inspect.getsource(tavily)


# ---------------------------------------------------------------------------
# A3: corroboration/host.py must be natively async
# ---------------------------------------------------------------------------


def test_corroborate_claim_is_coroutine_function():
    """corroborate_claim() must be an async function after Phase A."""
    from social_research_probe.corroboration.host import corroborate_claim

    assert inspect.iscoroutinefunction(corroborate_claim)


def test_host_does_not_call_run_coro():
    """host.py must not import or call run_coro after Phase A."""
    from social_research_probe.corroboration import host

    assert "run_coro" not in inspect.getsource(host)


def test_host_does_not_use_to_thread():
    """host.py must not use asyncio.to_thread after Phase A; backends are natively async."""
    from social_research_probe.corroboration import host

    assert "to_thread" not in inspect.getsource(host)


# ---------------------------------------------------------------------------
# A7: llm/ensemble.py must use asyncio subprocesses
# ---------------------------------------------------------------------------


def test_run_provider_is_coroutine_function():
    """ensemble._run_provider() must be a coroutine function."""
    from social_research_probe.llm.ensemble import _run_provider

    assert inspect.iscoroutinefunction(_run_provider)


def test_collect_responses_is_coroutine_function():
    """ensemble._collect_responses() must be a coroutine function."""
    from social_research_probe.llm.ensemble import _collect_responses

    assert inspect.iscoroutinefunction(_collect_responses)


def test_multi_llm_prompt_is_coroutine_function():
    """ensemble.multi_llm_prompt() must be a coroutine function."""
    from social_research_probe.llm.ensemble import multi_llm_prompt

    assert inspect.iscoroutinefunction(multi_llm_prompt)


def test_ensemble_does_not_use_thread_pool_executor():
    """ensemble.py must not use ThreadPoolExecutor after Phase A."""
    from social_research_probe.llm import ensemble

    assert "ThreadPoolExecutor" not in inspect.getsource(ensemble)


# ---------------------------------------------------------------------------
# A5: pipeline.run_research must be async
# ---------------------------------------------------------------------------


def test_run_research_is_coroutine_function():
    """pipeline.run_research() must be a coroutine function after Phase A."""
    from social_research_probe.pipeline import run_research

    assert inspect.iscoroutinefunction(run_research)


# ---------------------------------------------------------------------------
# A9: cli.py must use asyncio.run(), not run_coro
# ---------------------------------------------------------------------------


def test_pipeline_does_not_use_run_coro():
    """After Phase A, pipeline.py must not call run_coro."""
    from social_research_probe import pipeline

    assert "run_coro" not in inspect.getsource(pipeline)


# ---------------------------------------------------------------------------
# A-fix: YouTubeAdapter.enrich must be natively async (no nested asyncio.run)
# ---------------------------------------------------------------------------


def test_youtube_adapter_enrich_is_coroutine_function():
    """YouTubeAdapter.enrich() must be async so pipeline can await it directly."""
    from social_research_probe.platforms.youtube.adapter import YouTubeAdapter

    assert inspect.iscoroutinefunction(YouTubeAdapter.enrich)


def test_youtube_adapter_does_not_use_run_coro():
    """adapter.py must not call run_coro — it creates a nested event loop."""
    from social_research_probe.platforms.youtube import adapter

    assert "run_coro" not in inspect.getsource(adapter)


def test_corroborate_claims_cmd_does_not_use_run_coro():
    """After Phase A, commands/corroborate_claims.py must not call run_coro."""
    from social_research_probe.commands import corroborate_claims

    assert "run_coro" not in inspect.getsource(corroborate_claims)


def test_cli_does_not_import_run_coro():
    """After Phase A, cli.py must use asyncio.run() directly — not run_coro."""
    from social_research_probe import cli

    assert "run_coro" not in inspect.getsource(cli)
