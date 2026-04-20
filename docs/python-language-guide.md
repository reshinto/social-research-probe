# Python Language Guide

[Home](README.md) → Python Language Guide

This guide explains Python patterns as they are used in this codebase. It is written for contributors who know Python basics but are new to these specific idioms. Every example references an actual file in `social_research_probe/`.

See also: [Python Language Guide — Part 2](python-language-guide-2.md) (concepts 8–13: f-strings, list comprehensions, context managers, dataclasses, import order, `__init__.py`).

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

**How to read async code — `social_research_probe/llm/ensemble.py`:**

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

**The fan-out pattern — `social_research_probe/llm/ensemble.py`:**

```python
results = await asyncio.gather(
    *[_run_provider(name, prompt, task) for name in providers],
    return_exceptions=True,
)
```

This launches all `_run_provider` calls concurrently. If there are three providers (claude, gemini, codex), all three subprocess calls start immediately and run in parallel. `asyncio.gather` returns a list of results in the same order as the input coroutines.

**`return_exceptions=True`:** Normally, if one coroutine raises, `gather` cancels the rest and re-raises immediately. With `return_exceptions=True`, exceptions are returned as values in the result list instead of propagating — so one failing LLM call does not prevent the others from finishing.

**Another use — `social_research_probe/pipeline/enrichment.py`:**

```python
await asyncio.gather(
    *[_enrich_one(item, ...) for item in top5_items]
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

**Examples — `social_research_probe/stats/correlation.py`:**

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
    assert packet["items_top5"]
```

pytest sees the parameter name `tmp_data_dir`, finds the matching fixture, calls it, and passes the result in.

**How `conftest.py` works:** pytest automatically discovers `conftest.py` files. Any fixture defined there is available to all tests in the same directory and all subdirectories — no import needed.

**Gotcha:** Fixture scope defaults to `"function"` — the fixture runs fresh for every test. The fixtures in this project use function scope because they modify environment variables, which must not leak between tests.

---

## See also

- [Python Language Guide — Part 2](python-language-guide-2.md) — f-strings, list comprehensions, context managers, dataclasses vs TypedDicts, import order, `__init__.py`
- [Design Patterns](design-patterns.md) — how these conventions support the patterns
- [Testing](testing.md) — fixture conventions and async test setup
