"""Shared helpers for the evidence test suite.

Every evidence test sits on top of four deterministic primitives:

- ``golden(path)`` — load a recorded payload (JSON / bytes / text) from
  ``tests/fixtures/golden/``. Missing files raise immediately so tests fail
  loudly instead of silently skipping.
- ``frozen_clock(iso_date)`` — context manager that pins
  ``datetime.datetime.now`` / ``utcnow`` so any age / recency math is
  reproducible across machines and CI runs.
- ``canned_runner(responses)`` — a fake LLM runner that returns queued
  responses in order; raises when exhausted. Swaps in for the real
  :class:`LLMRunner` via fixture or monkeypatch.
- ``respx_golden(url, golden_path, method="GET")`` — one-liner HTTP replay
  that mocks a URL to return a recorded JSON payload.

An autouse ``_seed_everything`` fixture seeds ``random``, ``numpy.random``
and ``PYTHONHASHSEED`` so every evidence test starts from the same RNG
state, making parametrized outputs byte-identical across runs.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from social_research_probe.llm.base import LLMRunner
from social_research_probe.llm.types import AgenticSearchResult

GOLDEN_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "golden"


def _load_golden(path: str) -> object:
    """Resolve ``path`` under ``tests/fixtures/golden/`` and parse by extension.

    JSON files are parsed to Python objects (dict/list/…); text-shaped
    suffixes return ``str``; everything else returns raw ``bytes``. The
    return type is ``object`` so callers assert on the concrete type
    they expect — ``Any`` is banned by the repo's contract tests.
    """
    full = GOLDEN_ROOT / path
    if not full.exists():
        raise FileNotFoundError(
            f"golden file missing: {full} — record it via "
            f"scripts/record_golden.py before running this test"
        )
    if full.suffix == ".json":
        return json.loads(full.read_text(encoding="utf-8"))
    if full.suffix in {".txt", ".md", ".ascii", ".vtt", ".srt"}:
        return full.read_text(encoding="utf-8")
    return full.read_bytes()


@pytest.fixture
def golden():
    """Return a callable that loads a golden fixture by relative path."""
    return _load_golden


@contextmanager
def _frozen_clock(iso_date: str) -> Iterator[datetime]:
    """Pin ``datetime.now`` / ``utcnow`` to ``iso_date`` for the context body."""
    import datetime as _dt

    pinned = _dt.datetime.fromisoformat(iso_date)

    class _FrozenDateTime(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return pinned if tz is None else pinned.replace(tzinfo=tz)

        @classmethod
        def utcnow(cls):
            return pinned

    original = _dt.datetime
    _dt.datetime = _FrozenDateTime  # type: ignore[misc,assignment]
    try:
        yield pinned
    finally:
        _dt.datetime = original  # type: ignore[misc,assignment]


@pytest.fixture
def frozen_clock():
    """Return the ``frozen_clock(iso_date)`` context manager factory."""
    return _frozen_clock


class _CannedRunner(LLMRunner):
    """Fake :class:`LLMRunner` that replays a queue of canned responses.

    Supports ``run``, ``summarize_media``, and ``agentic_search`` — the three
    methods the evidence suite exercises. Each call pops the next item from
    the matching queue. Exhausting a queue raises :class:`AssertionError` so
    tests fail loudly rather than silently returning stale values.
    """

    name: str = "canned"
    supports_agentic_search: bool = True
    supports_media_url: bool = True

    def __init__(
        self,
        *,
        run_responses: list[dict] | None = None,
        media_responses: list[str | None] | None = None,
        search_responses: list[AgenticSearchResult] | None = None,
    ) -> None:
        self._run = list(run_responses or [])
        self._media = list(media_responses or [])
        self._search = list(search_responses or [])

    def health_check(self) -> bool:
        return True

    def run(self, prompt: str, *, schema: dict | None = None) -> dict:
        assert self._run, "canned_runner.run exhausted"
        return self._run.pop(0)

    async def summarize_media(
        self, url: str, *, word_limit: int = 100, timeout_s: float = 60.0
    ) -> str | None:
        assert self._media, "canned_runner.summarize_media exhausted"
        return self._media.pop(0)

    async def agentic_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        timeout_s: float = 60.0,
    ) -> AgenticSearchResult:
        assert self._search, "canned_runner.agentic_search exhausted"
        return self._search.pop(0)


@pytest.fixture
def canned_runner():
    """Return a factory that builds a :class:`_CannedRunner` per test."""
    return _CannedRunner


@contextmanager
def _respx_golden(
    url: str, golden_path: str, *, method: str = "GET", status_code: int = 200
) -> Iterator[None]:
    """Mock ``url`` to return the JSON body stored at ``golden_path``.

    Thin wrapper around :mod:`respx` so evidence tests can replay recorded
    API responses without rebuilding boilerplate in every file.
    """
    import httpx
    import respx

    payload = _load_golden(golden_path)
    with respx.mock:
        route = getattr(respx, method.lower())(url)
        route.mock(return_value=httpx.Response(status_code, json=payload))
        yield


@pytest.fixture
def respx_golden():
    """Return the ``respx_golden(url, golden_path)`` context manager factory."""
    return _respx_golden


@pytest.fixture(autouse=True)
def _seed_everything():
    """Seed ``random``, ``numpy.random``, and ``PYTHONHASHSEED`` to 0.

    Guarantees every evidence test sees the same RNG state on every run so
    parametrized outputs are byte-identical across machines.
    """
    random.seed(0)
    os.environ["PYTHONHASHSEED"] = "0"
    np.random.seed(0)
    yield
