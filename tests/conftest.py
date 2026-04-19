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

            def discard(self, v):  # type: ignore[override]
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

        sys.modules["rpds"] = _FakeRpds()  # type: ignore[assignment]


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect SRP data dir to a per-test temp path."""
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("SRP_DATA_DIR", str(data_dir))
    return data_dir
