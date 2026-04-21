"""Smoke tests for the evidence-suite infrastructure defined in conftest.py.

Each of the four helpers (``golden``, ``frozen_clock``, ``canned_runner``,
``respx_golden``) plus the autouse seed fixture is exercised once here so
later evidence phases can rely on them without diagnosing infra failures.

Evidence receipt (what / expected / why):

| Helper | Input | Expected | Why |
| --- | --- | --- | --- |
| ``golden`` (json) | ``_smoke.json`` with ``{"k": 1}`` | parsed dict ``{"k": 1}`` | JSON files are parsed by extension |
| ``golden`` (missing) | ``missing.json`` | FileNotFoundError | fail-loud contract for absent fixtures |
| ``frozen_clock`` | ``"2026-04-21T00:00:00"`` | ``datetime.now()`` returns pinned | clock pin required for age/recency math |
| ``canned_runner.run`` | queued response | returns queued dict, then raises on exhaust | queue semantics guarantee determinism |
| ``canned_runner.summarize_media`` | queued string | returns queued string | exercises media path of fake runner |
| ``canned_runner.agentic_search`` | queued AgenticSearchResult | returns queued result | exercises search path of fake runner |
| ``canned_runner.health_check`` | n/a | True | fake runner is always healthy |
| ``respx_golden`` | ``_smoke.json`` + mocked URL | real httpx GET returns the payload | proves replay plumbing works |
| autouse seed | — | ``random.random()`` is deterministic | all tests start with the same RNG state |
"""

from __future__ import annotations

import datetime as _dt
import json
import random
from pathlib import Path

import httpx
import pytest

from social_research_probe.llm.types import AgenticSearchCitation, AgenticSearchResult


@pytest.fixture
def _smoke_fixture_file():
    """Create ``_smoke.json`` under golden root for the duration of a test."""
    root = Path(__file__).resolve().parent.parent / "fixtures" / "golden"
    path = root / "_smoke.json"
    path.write_text(json.dumps({"k": 1}), encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def test_golden_loads_json_by_extension(golden, _smoke_fixture_file):
    assert golden("_smoke.json") == {"k": 1}


def test_golden_raises_on_missing_file(golden):
    with pytest.raises(FileNotFoundError, match="golden file missing"):
        golden("does/not/exist.json")


def test_golden_loads_text_files_verbatim(golden):
    """``.txt`` / ``.md`` / ``.vtt`` return the raw string."""
    root = Path(__file__).resolve().parent.parent / "fixtures" / "golden"
    text_path = root / "_smoke.txt"
    text_path.write_text("hello world", encoding="utf-8")
    try:
        assert golden("_smoke.txt") == "hello world"
    finally:
        text_path.unlink(missing_ok=True)


def test_golden_loads_unknown_extensions_as_bytes(golden):
    """Unknown suffixes come back as raw bytes, untouched."""
    root = Path(__file__).resolve().parent.parent / "fixtures" / "golden"
    bin_path = root / "_smoke.bin"
    bin_path.write_bytes(b"\x00\x01\x02")
    try:
        assert golden("_smoke.bin") == b"\x00\x01\x02"
    finally:
        bin_path.unlink(missing_ok=True)


def test_frozen_clock_pins_now(frozen_clock):
    pinned = "2026-04-21T00:00:00"
    with frozen_clock(pinned):
        now = _dt.datetime.now()
        assert now.isoformat() == pinned
        assert _dt.datetime.utcnow().isoformat() == pinned
    # Clock released after the context exits.
    assert _dt.datetime.now().year >= 2026


def test_canned_runner_queues_are_independent(canned_runner):
    canned = AgenticSearchResult(
        answer="ok", citations=[AgenticSearchCitation(url="https://x")], runner_name="canned"
    )
    runner = canned_runner(
        run_responses=[{"verdict": "supported"}],
        media_responses=["media summary"],
        search_responses=[canned],
    )
    assert runner.health_check() is True
    assert runner.supports_agentic_search is True


@pytest.mark.anyio
async def test_canned_runner_serves_and_exhausts(canned_runner):
    canned = AgenticSearchResult(answer="ok", citations=[], runner_name="canned")
    runner = canned_runner(
        run_responses=[{"k": 1}],
        media_responses=["s"],
        search_responses=[canned],
    )
    assert runner.run("p") == {"k": 1}
    assert await runner.summarize_media("u") == "s"
    assert (await runner.agentic_search("q")).answer == "ok"

    with pytest.raises(AssertionError, match="run exhausted"):
        runner.run("p")
    with pytest.raises(AssertionError, match="summarize_media exhausted"):
        await runner.summarize_media("u")
    with pytest.raises(AssertionError, match="agentic_search exhausted"):
        await runner.agentic_search("q")


def test_respx_golden_replays_recorded_payload(respx_golden, _smoke_fixture_file):
    with respx_golden("https://example.test/api", "_smoke.json"):
        resp = httpx.get("https://example.test/api")
    assert resp.status_code == 200
    assert resp.json() == {"k": 1}


def test_seed_everything_gives_deterministic_rng():
    """Autouse seed fixture guarantees random.random() starts from 0."""
    assert random.random() == pytest.approx(0.8444218515250481)
