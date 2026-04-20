# Python Language Guide — Part 2

[Home](README.md) → [Python Language Guide](python-language-guide.md) → Part 2

This is the second part of the Python Language Guide. It covers concepts 8–13: f-strings, list comprehensions, context managers, dataclasses vs TypedDicts, import order, and `__init__.py`. Every example references an actual file in `social_research_probe/`.

---

## 8. f-strings

**What it is:** A string literal prefixed with `f` that lets you embed Python expressions directly inside `{}` placeholders, evaluated at runtime.

**How to use them — `social_research_probe/utils/progress.py`:**

```python
def log(msg: str) -> None:
    print(msg, file=sys.stderr)
```

Called throughout the codebase like this (`social_research_probe/llm/ensemble.py`):

```python
log(f"[srp] LLM ({name}): {task}")
```

The `{name}` and `{task}` are replaced by the values of those variables at the time the string is created. No string concatenation or `.format()` calls needed.

**Format specifiers — `social_research_probe/stats/descriptive.py`:**

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

**Minimal `__init__.py` — `social_research_probe/stats/__init__.py`:**

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

- [Python Language Guide](python-language-guide.md) — Part 1: TypedDicts, Protocols, async/await, asyncio.gather, `from __future__`, type hints, pytest fixtures
- [Design Patterns](design-patterns.md) — how these conventions support the patterns
- [Testing](testing.md) — fixture conventions and async test setup
