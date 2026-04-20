# Python Language Guide

[Home](README.md) → Python Language Guide

This document covers the Python conventions used in this codebase. It is written for contributors who are comfortable with Python but are new to this project's specific patterns.

---

## Type Annotations

All public functions and dataclass fields are fully annotated. The project targets Python 3.11+, so use built-in generics (`list[str]`, `dict[str, int]`) rather than `List` / `Dict` from `typing`.

Use `from __future__ import annotations` at the top of every module to defer evaluation of annotations (required for forward references without quotes).

---

## TypedDicts

Packet structures are `TypedDict` rather than dataclasses because they serialise to JSON without a custom encoder and can be constructed from plain `dict` literals in tests.

```python
from typing import TypedDict

class ScoredItem(TypedDict):
    title: str
    score: float
    channel: str
```

Prefer `TypedDict` for data that crosses the pipeline boundary (items, packets, signals). Prefer dataclasses for internal configuration objects where attribute access and defaults matter.

---

## Protocols

Platform adapters and corroboration backends are typed as `Protocol` rather than abstract base classes. This allows test fakes to implement the protocol without inheriting from a production base class.

```python
from typing import Protocol

class PlatformAdapter(Protocol):
    def search(self, query: str, limits: FetchLimits) -> list[RawItem]: ...
    def health_check(self) -> bool: ...
```

---

## Async Patterns

The pipeline uses `asyncio` throughout. Key conventions:

- **`asyncio.gather`** for concurrent fan-out (LLM ensemble, corroboration backends).
- **`asyncio.Semaphore`** to limit concurrency for the outer topic loop.
- **`asyncio.to_thread`** for sync platform adapters that have not yet been converted to native async.
- **`asyncio.wait(FIRST_COMPLETED)`** for first-success races (LLM synthesis fallback).
- The top-level `main()` is an `async def` wrapped by `asyncio.run`.

Avoid `ThreadPoolExecutor` for I/O — use `asyncio.create_subprocess_exec` for subprocess-based LLM runners.

---

## Error Handling

Use the project's typed exceptions from `errors.py` (`ValidationError`, `AdapterError`, …) rather than bare `Exception`. Narrow exception handlers to the specific exception type:

```python
# good
try:
    result = await backend.corroborate(claim)
except ValidationError as exc:
    log(f"[srp] corroboration skipped: {exc}")

# bad — catches KeyboardInterrupt, SystemExit, etc.
try:
    result = await backend.corroborate(claim)
except Exception:
    pass
```

---

## pytest Fixtures

Fixtures are defined in `tests/conftest.py`. Key fixtures:

| Fixture | Description |
|---|---|
| `tmp_data_dir` | A temporary `Path` wired as `$SRP_DATA_DIR`; seeded with minimal topics/purposes |
| `fake_youtube` | Registers the fake YouTube adapter via `SRP_TEST_USE_FAKE_YOUTUBE=1` |
| `fake_corroboration` | Registers fake corroboration backends |

Reuse these fixtures rather than setting env vars or creating temp directories manually in individual tests.

---

## Async Tests

Use `pytest-asyncio` with `asyncio_mode = "auto"` (configured in `pyproject.toml`). Mark async test functions with `async def` — no `@pytest.mark.asyncio` decorator needed.

```python
async def test_run_research_returns_packet(tmp_data_dir):
    packet = await run_research(topic="ai", purposes=("latest-news",), data_dir=tmp_data_dir)
    assert packet["items_top5"]
```

---

## Module-level `__all__`

Public packages do not use `__all__`. Re-exports in `__init__.py` use explicit aliasing to satisfy ruff F401:

```python
from .utils import _emit as _emit  # explicit re-export
```

---

## Import Order

Imports are sorted by `ruff` (isort-compatible). The order is:

1. `from __future__ import annotations`
2. Standard library
3. Third-party packages
4. Local (`social_research_probe.*`)
5. Relative (`.submodule`)

Run `ruff check --fix` to auto-sort.

---

## See also

- [Design Patterns](design-patterns.md) — how these conventions support the patterns
- [Testing](testing.md) — fixture conventions and async test setup
