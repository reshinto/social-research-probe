# Python Language Guide

[Home](README.md) → Python Language Guide

This guide explains Python patterns as they are used in this codebase. It is written for contributors who know Python basics but are new to these specific idioms. Every example references an actual file in `social_research_probe/`.

**Contents:**

1. [TypedDicts](#1-typeddicts)
2. [Protocols](#2-protocols)
3. [async/await](#3-asyncawait)
4. [asyncio.gather](#4-asynciogather)
5. [`from __future__ import annotations`](#5-from-__future__-import-annotations)
6. [Type hints](#6-type-hints)
7. [pytest fixtures](#7-pytest-fixtures)
8. [f-strings](#8-f-strings)
9. [List comprehensions](#9-list-comprehensions)
10. [Context managers](#10-context-managers)
11. [Dataclasses vs TypedDicts](#11-dataclasses-vs-typeddicts)
12. [Import order](#12-import-order)
13. [`__init__.py`](#13-__init__py)

---

## 1. TypedDicts

**What it is:** A way to declare the expected keys and value types of a plain Python `dict`, so that type checkers can verify you are not mistyping key names or storing the wrong type.

**Why not a plain `dict`?** A plain `dict[str, Any]` gives no information about what keys exist or what types they hold. A `TypedDict` documents the shape and lets tools like `mypy` or `pyright` catch mistakes at review time rather than at runtime.

**Definition and use — `social_research_probe/types.py`:**

```python
from typing import TypedDict

class ScoreBreakdown(TypedDict):
    trust: float
    trend: float
    opportunity: float
    overall: float
```

You construct one just like a plain dict:

```python
breakdown: ScoreBreakdown = {
    "trust": 0.82,
    "trend": 0.61,
    "opportunity": 0.74,
    "overall": 0.73,
}
```

You access fields the same way: `breakdown["trust"]`.

**`total=False`:** Several TypedDicts in this project use `total=False`, meaning all keys are optional. `ScoredItem` and `AdapterConfig` are examples — useful for structures built up incrementally or where not every field is always populated.

**Gotcha:** A `TypedDict` is only a type-checker hint — Python does not enforce the shape at runtime. If you construct a dict with wrong keys, Python will not raise an error; only a type checker will catch it.

---

## 2. Protocols

**What it is:** A way to define an interface — a set of methods a type must have — without requiring that type to inherit from anything.

**Protocols vs abstract base classes:** An abstract base class (ABC) requires every implementation to subclass it. A `Protocol` requires only that the object has the right methods — it does not matter how the class is defined. This is called structural typing, or "duck typing with type-checker support."

**How the codebase uses ABCs — `social_research_probe/platforms/base.py`:**

The codebase uses ABCs for platform adapters because each adapter must also carry class-level metadata (`name`, `default_limits`) enforced at instantiation time:

```python
from abc import ABC, abstractmethod

class PlatformAdapter(ABC):
    @abstractmethod
    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]: ...

    @abstractmethod
    async def enrich(self, items: list[RawItem]) -> list[RawItem]: ...
```

The benefit: forgetting to implement `search` raises `TypeError` when the class is instantiated — you get an early, clear error rather than a confusing `AttributeError` at the call site.

LLM runners follow the same ABC pattern in `social_research_probe/llm/base.py`.

**When to prefer Protocol instead:** Use `Protocol` when you want to accept any object that has a method, without coupling to your class hierarchy. A test fake does not need to subclass `PlatformAdapter` to satisfy a `Protocol`-typed parameter.

**Gotcha:** You cannot instantiate an ABC or Protocol directly — only concrete subclasses that implement all abstract methods can be instantiated.

---

## 3. async/await

**What it is:** A way to write code that can pause while waiting for slow I/O (network calls, subprocess output) and let other work run in the meantime, all in a single thread.

**Why it matters for I/O-bound work:** When your code calls a network API, the CPU sits idle waiting for the response. With `async/await`, Python can switch to running other code during that wait. This is why the pipeline can fetch transcripts, call LLM CLIs, and run corroboration checks concurrently.

**How to read async code — `social_research_probe/services/llm/ensemble.py`:**

```python
async def _run_provider(name: str, prompt: str, task: str = "generating response") -> str | None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(stdin_data), timeout=_TIMEOUT)
    return stdout.decode().strip()
```

- `async def` declares a coroutine — a function that can pause.
- `await` pauses this coroutine until the awaited thing completes. While paused, other coroutines can run.
- The function returns `str | None`, not a coroutine object. You only see the raw coroutine object if you forget to `await` it.

**Entry point:** The top-level `main()` in the CLI is `async def` and is started with `asyncio.run(main())`. Everything inside the pipeline descends from that single `asyncio.run` call.

**Gotcha:** You can only `await` inside an `async def` function. Calling `async def something()` without `await` gives you a coroutine object, not the result — and Python will warn that it was never awaited.

---

## 4. asyncio.gather

**What it is:** A function that runs multiple coroutines at the same time and collects all their results.

**The fan-out pattern — `social_research_probe/services/llm/ensemble.py`:**

```python
results = await asyncio.gather(
    *[_run_provider(name, prompt, task) for name in providers],
    return_exceptions=True,
)
```

This launches all `_run_provider` calls concurrently. If there are three providers (claude, gemini, codex), all three subprocess calls start immediately and run in parallel. `asyncio.gather` returns a list of results in the same order as the input coroutines.

**`return_exceptions=True`:** Normally, if one coroutine raises, `gather` cancels the rest and re-raises immediately. With `return_exceptions=True`, exceptions are returned as values in the result list instead of propagating — so one failing LLM call does not prevent the others from finishing.

**Another use — `social_research_probe/services/enriching/summary.py`:**

```python
await asyncio.gather(
    *[_enrich_one(item, ...) for item in top_n_items]
)
```

All five enrichment tasks (transcript fetch + LLM summary per item) run concurrently, halving the total wall-clock time compared to sequential processing.

**Gotcha:** `asyncio.gather` runs coroutines concurrently in a single thread — it is not parallelism. CPU-bound work does not benefit from it. It is ideal for I/O-bound work (network, subprocess) where the thread spends most of its time waiting.

---

## 5. `from __future__ import annotations`

**What it is:** A single import that changes how Python handles type annotations in that file — it defers evaluating them until they are actually needed.

**Why it is at the top of every file:** Without it, Python evaluates annotations eagerly at import time. This means you cannot write `list[str]` as a return type in older Python versions, and you cannot reference a class by name before it is defined. With deferred evaluation, all annotations are treated as strings internally and resolved lazily, so forward references and modern syntax work everywhere.

**Example — `social_research_probe/types.py`:**

```python
from __future__ import annotations

# JSONValue references itself (a forward reference) — valid because annotations are deferred.
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
```

Without deferred annotations, this self-referential type alias would require workarounds on Python 3.9 and earlier.

**Gotcha:** Because annotations are deferred, `get_type_hints()` (used by some frameworks to read annotations at runtime) requires passing `localns`/`globalns` to resolve them. This is rarely a concern here since annotations are used only for static checking.

---

## 6. Type hints

**What it is:** Optional annotations that tell you (and tools) what types a variable, parameter, or return value should be.

**Reading common forms:**

| Annotation | Meaning |
|---|---|
| `list[str]` | A list where every element is a string |
| `dict[str, Any]` | A dict with string keys and values of any type |
| `str \| None` | Either a string or None (Python 3.10+ union syntax) |
| `Optional[str]` | Same as `str \| None` (older style from `typing`) |
| `float \| None` | A float or None — common for computed fields that may be absent |

**Examples — `social_research_probe/technologies/statistics/correlation.py`:**

```python
def run(
    series_a: list[float],
    series_b: list[float],
    label_a: str = "a",
    label_b: str = "b",
) -> list[StatResult]:
```

- `series_a: list[float]` — the caller must pass a list of floats.
- `-> list[StatResult]` — the function always returns a list (possibly empty).

**`Any`:** `Any` is an escape hatch that disables type checking for that value. It appears in `JSONValue` (`social_research_probe/types.py`) because JSON can hold any JSON-legal value. Avoid `Any` in new code — it removes the type checker's ability to catch mistakes.

**Gotcha:** Type hints are not enforced at runtime. Passing a string where `float` is expected raises no error at call time — only a type checker will flag it. Think of them as documentation that tools can verify.

---

## 7. pytest fixtures

**What it is:** A function decorated with `@pytest.fixture` that sets up (and optionally tears down) shared test state. Test functions declare the fixtures they need as parameters and pytest injects them automatically.

**Defining a fixture — `tests/conftest.py`:**

```python
@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect SRP data dir to a per-test temp path."""
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("SRP_DATA_DIR", str(data_dir))
    return data_dir
```

- `tmp_path` and `monkeypatch` are built-in pytest fixtures injected by pytest itself.
- `monkeypatch.setenv` sets an environment variable for the duration of the test and automatically undoes it afterwards — no manual cleanup needed.
- The fixture `return`s the path so the test can write files into it.

**Using a fixture in a test:**

```python
async def test_run_research_returns_packet(tmp_data_dir):
    packet = await run_research(topic="ai", purposes=("latest-news",), data_dir=tmp_data_dir)
    assert packet["items_top_n"]
```

pytest sees the parameter name `tmp_data_dir`, finds the matching fixture, calls it, and passes the result in.

**How `conftest.py` works:** pytest automatically discovers `conftest.py` files. Any fixture defined there is available to all tests in the same directory and all subdirectories — no import needed.

**Gotcha:** Fixture scope defaults to `"function"` — the fixture runs fresh for every test. The fixtures in this project use function scope because they modify environment variables, which must not leak between tests.

---

## 8. f-strings

**What it is:** A string literal prefixed with `f` that lets you embed Python expressions directly inside `{}` placeholders, evaluated at runtime.

**How to use them — `social_research_probe/utils/progress.py`:**

```python
def log(msg: str) -> None:
    print(msg, file=sys.stderr)
```

Called throughout the codebase like this (`social_research_probe/services/llm/ensemble.py`):

```python
log(f"[srp] LLM ({name}): {task}")
```

The `{name}` and `{task}` are replaced by the values of those variables at the time the string is created. No string concatenation or `.format()` calls needed.

**Format specifiers — `social_research_probe/technologies/statistics/descriptive.py`:**

```python
caption=f"Mean {label}: {mean_val:,.4g}"
```

The `:,.4g` after `mean_val` is a format spec: `,` adds thousands separators, `.4g` means 4 significant figures. The result for `mean_val=12345.6789` would be `"12,350"`.

Common format specs:

| Spec | Effect |
|---|---|
| `:.2f` | Two decimal places: `0.61` |
| `:.2%` | Percentage with two decimals: `61.23%` |
| `:,.4g` | 4 significant figures with thousands separator |
| `!r` | `repr()` of the value (adds quotes around strings) |

**Gotcha:** f-strings evaluate expressions eagerly when the line runs — you cannot use them as lazy templates stored for later use. If the variable changes after you create the string, the string does not update.

---

## 9. List comprehensions

**What it is:** A concise way to build a new list by transforming or filtering items from an existing iterable, in a single expression.

**Basic form:** `[expression for item in iterable if condition]`

**Examples from the codebase — `social_research_probe/synthesize/evidence.py`:**

```python
ages = [max(0.0, (now - s.upload_date).days) for s in signals if s.upload_date]
```

Plain-English reading: "For each signal `s` in `signals`, if `s.upload_date` is not None, compute the number of days since upload (clamped to 0) and collect those into a list."

Another example — `social_research_probe/validation/claims.py`:

```python
sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
```

This splits text on sentence boundaries, strips whitespace from each piece, and keeps only non-empty results — all in one line.

**Set comprehension:** The same syntax with `{}` instead of `[]` produces a set (deduplicated):

```python
unique = len({it.author_name for it in items if it.author_name})
```

(`social_research_probe/synthesize/evidence.py`) — counts distinct author names by building a set of names, discarding `None`/empty values.

**Gotcha:** List comprehensions are for transformation and filtering. If you need to accumulate a running total or carry state between iterations, a regular `for` loop is clearer. Deeply nested comprehensions are hard to read — extract a helper function instead.

---

## 10. Context managers

**What it is:** A block introduced with `with` that guarantees setup and teardown happen correctly — even if an exception is raised inside the block.

**Opening files — `social_research_probe/utils/io.py`:**

```python
with open(path, encoding="utf-8") as fh:
    return json.load(fh)
```

When the `with` block exits — whether normally or via an exception — Python automatically calls `fh.close()`. You never risk leaving a file handle open.

**Suppressing specific exceptions — `social_research_probe/utils/cache.py`:**

```python
with contextlib.suppress(FileNotFoundError):
    path.unlink()
```

`contextlib.suppress` is a context manager that swallows the listed exception type if it is raised inside the block. Here it means "delete the file if it exists; ignore silently if it doesn't."

**Why context managers exist:** They encode the "acquire / use / release" pattern in a reusable, composable way. Without them, every caller would need to write `try/finally` blocks manually, and it is easy to forget the `finally` clause.

**Custom context managers:** You can write your own using `contextlib.contextmanager` (a decorator) or by implementing `__enter__` and `__exit__` on a class. This project does not define custom context managers, but uses `contextlib.suppress` from the standard library.

**Gotcha:** The `as fh` part is optional. `with some_lock:` (without `as`) acquires and releases the lock without binding any return value.

---

## 11. Dataclasses vs TypedDicts

**The short answer:** TypedDicts are for data that crosses process or serialisation boundaries (JSON in, JSON out). Dataclasses are for internal objects where you want attribute access, defaults, and method support.

**TypedDicts in this project — `social_research_probe/types.py`:**

```python
class ScoredItem(TypedDict, total=False):
    title: str
    channel: str
    url: str
    scores: ScoreBreakdown
```

`ScoredItem` is stored in the research packet, serialised to JSON, and sent to the renderer. Using a `TypedDict` means `json.dumps(item)` works without a custom encoder, and you can construct one with a plain dict literal in tests.

**Dataclasses in this project — `social_research_probe/platforms/base.py`:**

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class FetchLimits:
    max_items: int = 20
    recency_days: int | None = 90
```

`FetchLimits` is an internal configuration object. `@dataclass` gives it:
- A generated `__init__` that accepts keyword arguments.
- A generated `__repr__` for readable debug output.
- `frozen=True` makes instances immutable (hashable, safe to use as dict keys).

It would be awkward as a `TypedDict` because dataclasses support default values per field, whereas TypedDicts require `total=False` for all-or-nothing optionality.

**Decision rule used in this project:**

| Use | When |
|---|---|
| `TypedDict` | Data leaves or enters the process (JSON packets, API responses, state files) |
| `dataclass` | Internal configuration or value objects that benefit from defaults, methods, or immutability |

**Gotcha:** You cannot add methods to a `TypedDict`. If you find yourself wanting to add helper methods, switch to a dataclass.

---

## 12. Import order

**What it is:** A standard ordering for the `import` statements at the top of every Python file, enforced automatically by the `ruff` linter.

**The order — `social_research_probe/config.py`:**

```python
from __future__ import annotations   # 1. future imports always first

import copy                           # 2. standard library
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from social_research_probe.types import (   # 3. local package imports
    AdapterConfig,
    AppConfig,
)
```

Third-party libraries (e.g. `import rapidfuzz`) would appear between the standard library block and the local package block.

**Why this order matters:**

1. `from __future__ import annotations` must be the very first statement to take effect. If it appears after other imports, Python ignores it.
2. Standard library first means the reader can immediately see which built-ins are used.
3. Third-party after standard library separates "what Python ships" from "what you installed."
4. Local imports last clearly identify which code is in this project.

**Blank lines:** Each group is separated by one blank line. Mixing groups (e.g. a standard library import between two local imports) will cause `ruff check` to fail.

**Enforcement:** Run `ruff check --fix` to auto-sort imports. The CI pipeline blocks merges with unsorted imports.

**Gotcha:** Circular imports — where module A imports B and B imports A — are often discovered when you reorganise imports. The fix is usually to move the shared type to a third module (this project keeps shared types in `types.py`) or to use a local import inside a function to break the cycle.

---

## 13. `__init__.py`

**What it is:** A file that marks a directory as a Python package, making it importable. It also controls what is visible to importers of the package.

**Why it is needed:** Without `__init__.py`, Python (in most configurations) will not treat the directory as a package, and `from social_research_probe.stats import descriptive` will fail.

**Minimal `__init__.py` — `social_research_probe/technologies/statistics/__init__.py`:**

```python
"""Statistical analysis package for social-media signal data."""
```

This file contains only a docstring. Its presence tells Python that `stats/` is a package. It does not re-export anything — callers import submodules directly (e.g. `from social_research_probe.stats import descriptive`).

**Explicit re-exports — `social_research_probe/platforms/youtube/__init__.py`:**

```python
from social_research_probe.platforms.youtube.adapter import YouTubeAdapter

__all__ = ["YouTubeAdapter"]
```

This re-exports `YouTubeAdapter` so callers can write:

```python
from social_research_probe.platforms.youtube import YouTubeAdapter
```

instead of the longer:

```python
from social_research_probe.platforms.youtube.adapter import YouTubeAdapter
```

It also registers the adapter as a side-effect of importing the subpackage.

**Re-export alias pattern:** When a module re-exports a name without `__all__`, `ruff` flags it as an unused import (F401). The convention in this project is to alias the name to itself to mark the intent explicitly:

```python
from .utils import _emit as _emit
```

The `as _emit` tells `ruff` this is an intentional re-export, not a stale import.

**Gotcha:** Putting too much code in `__init__.py` (initialisation logic, class definitions) makes it hard to reason about import order. Keep `__init__.py` files small — a docstring and explicit re-exports only.

---

## See also

- [Design Patterns](design-patterns.md) — how these conventions support the patterns
- [Testing](testing.md) — fixture conventions and async test setup
- [Architecture](architecture.md) — where these patterns fit in the system design
