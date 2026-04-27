"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Python 3.14.0a1t (the free-threaded alpha) is missing _PyType_Freeze, which
# rpds-py 0.30.0 references at dlopen time. Provide a lightweight pure-Python
# stub so jsonschema can be imported in tests without a binary-compatible wheel.
if "rpds" not in sys.modules:
    try:
        import rpds as _rpds_check  # noqa: F401
    except ImportError:

        class _HTM(dict):
            @classmethod
            def convert(cls, data=None):
                return cls(data or {})

            def insert(self, k, v):
                r = _HTM(self)
                r[k] = v
                return r

            def remove(self, k):
                r = _HTM(self)
                r.pop(k, None)
                return r

        class _HTS(set):
            @classmethod
            def convert(cls, data=None):
                return cls(data or [])

            def insert(self, v):
                r = _HTS(self)
                r.add(v)
                return r

            def remove(self, v):
                r = _HTS(self)
                set.discard(r, v)
                return r

            def discard(self, v):
                r = _HTS(self)
                set.discard(r, v)
                return r

        class _L(list):
            @classmethod
            def convert(cls, data=None):
                return cls(data or [])

        class _FakeRpds:
            HashTrieMap = _HTM
            HashTrieSet = _HTS
            List = _L

        sys.modules["rpds"] = _FakeRpds()


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect SRP data dir to a per-test temp path."""
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("SRP_DATA_DIR", str(data_dir))
    return data_dir


@pytest.fixture(autouse=True)
def _disable_pipeline_cache_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable disk caches in tests unless a test explicitly re-enables them.

    Without this, tests that don't patch SRP_DATA_DIR would write cache entries
    into the user's real ~/.cache/srp directory and cross-pollute each other.
    Tests that exercise caching behaviour call ``monkeypatch.delenv`` on
    ``SRP_DISABLE_CACHE`` and point ``SRP_DATA_DIR`` at ``tmp_path``.
    """
    monkeypatch.setenv("SRP_DISABLE_CACHE", "1")


@pytest.fixture(autouse=True)
def _reset_whisper_model_cache() -> None:
    """Clear the in-process Whisper model cache between tests.

    The cache key uses ``id(module)`` which CPython can reuse across freed
    objects, so a stale mock model from an earlier test could masquerade as a
    hit for a later test's fresh mock. Clearing avoids that cross-contamination.
    """
    from social_research_probe.technologies.transcript_fetch import whisper

    whisper._MODEL_CACHE.clear()
    yield
    whisper._MODEL_CACHE.clear()
