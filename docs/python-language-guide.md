[Back to docs index](README.md)

# Python Language Guide

![Python concepts used here](diagrams/python-flow.svg)

This guide teaches the Python concepts used in Social Research Probe. It is
written for someone who has never used Python before but wants enough context to
read, debug, and extend this project.

The goal is not to memorize every Python feature. The goal is to understand the
language patterns this repository actually uses: modules, imports, functions,
type hints, dataclasses, classes, async code, filesystem paths, JSON/TOML,
subprocesses, exceptions, and tests.

## How Python code is organized

Python source files end in `.py`. One `.py` file is a module. A folder of Python
modules is a package when Python can import it by name. This project package is
`social_research_probe`.

Example:

```text
social_research_probe/
  config.py
  commands/
    research.py
  services/
    analyzing/
      statistics.py
  technologies/
    statistics/
      descriptive.py
```

You import code from modules instead of copying it:

```python
from social_research_probe.config import load_active_config
```

This means: find `social_research_probe/config.py` and import the object named
`load_active_config`.

Best practice in this repository:

| Practice                                              | Why                                                                      |
| ----------------------------------------------------- | ------------------------------------------------------------------------ |
| Use absolute imports from `social_research_probe...`. | They are clear and work reliably in tests.                               |
| Import the narrow thing you need.                     | Readers can see where names come from.                                   |
| Avoid `from module import *`.                         | Wildcard imports hide dependencies.                                      |
| Keep imports cheap.                                   | Importing a file should not call APIs, run subprocesses, or write files. |

Expensive work should happen inside functions or methods that are called
deliberately.

## Running Python code

The installed CLI ultimately runs Python functions. A command such as:

```bash
srp research "AI agents" "latest-news"
```

enters the CLI parser, creates a command object, and dispatches into command and
platform code. Python code is executed top to bottom inside the function or
method being called.

`social_research_probe/__main__.py` and CLI modules exist so the package can be
run as a command. Most contributors do not need to edit those first; start with
the command, service, platform, or technology module related to the behavior.

## Values and variables

A variable is a name that points to a value:

```python
topic = "AI agents"
max_items = 20
enabled = True
```

Python decides the runtime type from the value. Type hints can document what is
expected, but the assignment itself is still dynamic.

Common value types in this project:

| Type    | Example                | Used for                             |
| ------- | ---------------------- | ------------------------------------ |
| `str`   | `"AI agents"`          | Topics, URLs, config keys, captions. |
| `int`   | `20`                   | Counts, ranks, limits.               |
| `float` | `0.82`                 | Scores, ratios, statistics.          |
| `bool`  | `True`                 | Gates and flags.                     |
| `None`  | `None`                 | Missing value or no result.          |
| `list`  | `[item1, item2]`       | Ordered collections.                 |
| `dict`  | `{"topic": "AI"}`      | Structured JSON-like data.           |
| `tuple` | `("overall", "trust")` | Fixed grouped values.                |
| `Path`  | `Path("report.html")`  | Filesystem paths.                    |

## Strings

Strings hold text:

```python
title = "Understanding AI agents"
```

Use f-strings to insert values into text:

```python
caption = f"Mean overall score: {mean:.4f}"
```

`{mean:.4f}` means format the number with four digits after the decimal point.
This pattern appears in statistics captions and report text.

Use `.strip()` to remove surrounding whitespace and `.replace()` to change text:

```python
safe_name = name.strip().replace(" ", "-")
```

## Lists

A list is an ordered collection:

```python
scores = [0.91, 0.84, 0.52]
```

Lists are used for fetched items, scored items, service results, chart outputs,
and statistical series. You can loop over a list:

```python
for score in scores:
    print(score)
```

You can build a new list with a list comprehension:

```python
titles = [item["title"] for item in items]
```

This means: for each `item` in `items`, take `item["title"]`, and collect the
results into a new list.

Use list comprehensions when the transformation is simple. Use a normal `for`
loop when the logic needs multiple steps, error handling, or comments.

## Dictionaries

A dictionary maps keys to values:

```python
item = {
    "title": "Understanding AI agents",
    "url": "https://example.com/video",
    "scores": {"overall": 0.84, "trust": 0.75, "trend": 0.91, "opportunity": 0.62},
}
```

The project uses dictionaries for JSON-like packets, config fragments, raw API
responses, and report data.

Access a required key with square brackets:

```python
title = item["title"]
```

Access an optional key with `.get()`:

```python
features = item.get("features") or {}
velocity = features.get("view_velocity", 0.0)
```

Use `.get()` when missing data is expected. Use square brackets when missing
data should be treated as a bug.

## Tuples and sets

A tuple is an ordered group that is usually treated as fixed:

```python
NUMERIC_TARGETS = ("overall", "trust", "trend")
```

Tuples are useful for constants and small return values.

A set stores unique values:

```python
seen_urls = set()
seen_urls.add(url)
```

Use a set when you need fast membership checks or duplicate removal.

## Conditionals

`if`, `elif`, and `else` choose behavior:

```python
if not items:
    return {"highlights": [], "low_confidence": True}
elif len(items) < 5:
    return {"low_confidence": True}
else:
    return {"low_confidence": False}
```

Python treats empty strings, empty lists, empty dictionaries, `0`, `False`, and
`None` as false-like. That is why `if not items:` means "if the list is empty."

Be explicit when the difference matters:

```python
if value is None:
    ...
```

Use `is None` for missing values. Do not use `== None`.

## Loops

Use `for` when iterating over known items:

```python
for item in scored_items:
    ...
```

Use `enumerate` when you need the index and value:

```python
for rank, item in enumerate(scored_items):
    item["rank"] = rank
```

Use `zip` when walking multiple lists together:

```python
for velocity, age in zip(view_velocity, age_days, strict=True):
    views.append(velocity * age)
```

`strict=True` tells Python to raise an error if the lists have different
lengths. This is useful when arrays must stay aligned by item row.

## Functions

A function packages reusable behavior:

```python
def overall_score(*, trust: float, trend: float, opportunity: float) -> float:
    return 0.45 * trust + 0.30 * trend + 0.25 * opportunity
```

Important parts:

| Part            | Meaning                                          |
| --------------- | ------------------------------------------------ |
| `def`           | Defines a function.                              |
| `overall_score` | Function name.                                   |
| `trust: float`  | Parameter named `trust`, expected to be a float. |
| `-> float`      | Function should return a float.                  |
| `return`        | Sends a value back to the caller.                |
| `*`             | Forces callers to use keyword arguments.         |

The `*` matters:

```python
overall_score(trust=0.9, trend=0.6, opportunity=0.7)
```

This is clearer than positional calls because it prevents accidentally swapping
similar numeric values.

Good functions in this repository are usually small and testable. They take
inputs, return outputs, and avoid hidden global state.

## Default arguments

Functions can define defaults:

```python
def run(data: list[float], label: str = "values") -> list[StatResult]:
    ...
```

Callers can omit `label`, and the function will use `"values"`.

Avoid mutable defaults such as `items: list = []`. A mutable default can be
shared across calls. Use `None` and create the list inside the function if you
need that pattern.

## Type hints

Type hints document expected shapes:

```python
def score_items(items: list[dict]) -> list[dict]:
    ...
```

Python does not enforce all type hints at runtime. They help humans, editors,
linters, and tests.

Common type hints in this repository:

| Hint               | Meaning                                      |
| ------------------ | -------------------------------------------- | ------------------------ |
| `str`              | Text.                                        |
| `int`              | Integer.                                     |
| `float`            | Decimal number.                              |
| `bool`             | True or false.                               |
| `Path`             | Filesystem path object.                      |
| `list[dict]`       | List of dictionaries.                        |
| `dict[str, list]`  | Dictionary with string keys and list values. |
| `object`           | Any Python value, intentionally broad.       |
| `str               | None`                                        | String or missing value. |
| `list[StatResult]` | List containing `StatResult` objects.        |

Use a specific type when the function has a specific contract. Use `object` at
boundaries where the service intentionally validates unknown input.

## `None` and union types

`None` means no value:

```python
cached = get_json(cache, key)
if cached is not None:
    return cached
```

The type hint `dict | None` means the value may be a dictionary or `None`.
Always handle the `None` case before using it as a dictionary.

## Dataclasses

Dataclasses are classes designed mainly to hold data:

```python
from dataclasses import dataclass


@dataclass
class TechResult:
    tech_name: str
    output: object
    success: bool
```

The `@dataclass` decorator makes Python generate an initializer:

```python
result = TechResult(tech_name="charts", output={}, success=True)
```

This is better than a loose dictionary when the fields are part of a contract.
The repository uses dataclasses for platform items, pipeline state, service
results, technology results, and evaluation records.

## Frozen dataclasses

Some dataclasses are declared with `frozen=True`:

```python
@dataclass(frozen=True)
class FetchLimits:
    max_items: int = 20
```

Frozen means fields cannot be changed after creation. Use this for small
configuration-like records that should not be mutated accidentally.

## Classes

A class defines a kind of object with data and behavior:

```python
class StatisticsService(BaseService):
    service_name = "youtube.analyzing.statistics"

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        ...
```

`StatisticsService(BaseService)` means `StatisticsService` inherits from
`BaseService`. It gets the base behavior and customizes the parts it needs.

Use classes in this project when there is a stable interface with multiple
implementations:

| Interface        | Implementations                                              |
| ---------------- | ------------------------------------------------------------ |
| `BaseService`    | scoring, transcript, summary, statistics, charts, reporting. |
| `BaseTechnology` | provider adapters, LLM runners, chart renderers.             |
| `PlatformClient` | platform source adapters.                                    |
| `BaseStage`      | pipeline stages.                                             |

Do not create a class just to group one small function. Use a function for pure
logic unless shared interface behavior is needed.

## `self`

Instance methods include `self`:

```python
class Example:
    def greet(self, name: str) -> str:
        return f"Hello {name}"
```

`self` is the current object. You do not pass it manually:

```python
example = Example()
example.greet("Ada")
```

Python passes `example` as `self`.

## Class variables

The repository often uses `ClassVar` for names and config keys:

```python
from typing import ClassVar


class ChartsService(BaseService):
    service_name: ClassVar[str] = "youtube.analyzing.charts"
    enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"
```

`ClassVar` means the value belongs to the class, not to one instance. This is
useful for identifiers shared by all instances of a service or technology.

## Abstract base classes

An abstract base class defines required methods:

```python
from abc import ABC, abstractmethod


class BaseTechnology(ABC):
    @abstractmethod
    async def _execute(self, data):
        ...
```

A subclass must implement the abstract method. This lets the project define
contracts such as "every technology must know how to execute."

Why use this instead of informal conventions: mistakes fail earlier. If a new
technology forgets `_execute`, Python can reject the incomplete class.

## Decorators

A decorator modifies a function or class:

```python
@dataclass
class StatResult:
    name: str
    value: float
```

`@dataclass` is a decorator. Pytest fixtures and marks also use decorators:

```python
@pytest.fixture
def tmp_data_dir(tmp_path):
    ...
```

Read decorators as "wrap this object with extra behavior." Do not add decorators
unless you understand what behavior they add.

## Async and await

`async def` defines a coroutine function:

```python
async def execute_one(self, data: object) -> ServiceResult:
    ...
```

Calling it creates a coroutine. `await` runs it and waits for the result:

```python
result = await service.execute_one(item)
```

Async is used because many tasks wait on IO: platform APIs, transcript fetches,
LLM runner subprocesses, web search providers, and file rendering. Async lets
independent waits overlap.

The key idea: an async function can pause at `await` while some other async work
runs. That is different from a normal blocking function, where Python sits and
waits until the call returns.

Normal function:

```python
def compute_trust(extras: dict) -> float:
    return trust_score(...)
```

Async function:

```python
async def execute_one(self, data: object) -> ServiceResult:
    transcript = await transcript_provider.execute(data)
    return ServiceResult(...)
```

Use normal functions for CPU-only calculations such as scoring, z-scores, and
statistics formulas. Use async functions for orchestration that may call network
providers, subprocess runners, transcript fetchers, or other async services.

In this repository, most service entry points are async because the pipeline
needs a consistent way to run services whether the current implementation is
local, network-backed, subprocess-backed, or a mix.

Important rule: if a function is declared with `async def`, callers must use
`await` unless they are intentionally passing the coroutine object to a scheduler
such as `asyncio.gather`.

Wrong:

```python
result = service.execute_one(item)  # result is a coroutine, not the final value
```

Right:

```python
result = await service.execute_one(item)
```

If you forget `await`, later code will often fail in confusing ways because it
receives a coroutine object instead of a `ServiceResult`.

## Running tasks concurrently

`asyncio.gather` runs several awaitable tasks concurrently:

```python
results = await asyncio.gather(
    *(service.execute_one(item) for item in items)
)
```

This does not make CPU-heavy math faster. It helps when tasks spend time waiting
for external work.

`asyncio.gather` returns results in the same order as the awaitables passed into
it. That matters when outputs must stay aligned with inputs.

Example:

```python
tech_results = await asyncio.gather(
    *(run_technology(tech) for tech in technologies)
)
```

If `technologies[0]` finishes last, its result still appears at
`tech_results[0]`. Concurrency changes completion time, not result ordering.

Also understand failure behavior. If one gathered coroutine raises and the error
is not caught inside that coroutine, `gather` can raise too. This project often
catches exceptions inside the per-technology wrapper so one provider failure
becomes a failed `TechResult` instead of crashing the entire service batch.

That is why service code commonly uses this shape:

```python
async def _run(tech):
    try:
        output = await tech.execute(data)
        return TechResult(tech_name=tech.name, output=output, success=True)
    except Exception as exc:
        return TechResult(tech_name=tech.name, output=None, success=False, error=str(exc))
```

Each technology gets its own failure boundary.

## Running blocking code from async code

Some libraries are synchronous. `asyncio.to_thread` runs blocking work in a
thread so the async event loop can keep moving:

```python
charts = await asyncio.to_thread(render_all, items, charts_dir)
```

Use this when calling CPU or blocking IO functions from async service code.

Without `to_thread`, a blocking function can freeze the event loop. For example,
chart rendering and some transcript or audio operations use normal synchronous
libraries. Wrapping them with `asyncio.to_thread` lets the service keep an async
interface while the blocking work runs outside the event loop thread.

Use `to_thread` for:

| Good use                                                  | Why                                    |
| --------------------------------------------------------- | -------------------------------------- |
| Rendering charts with synchronous plotting code.          | Plotting can block.                    |
| Running local transcription helpers that are synchronous. | The event loop should stay responsive. |
| Writing a report with a synchronous renderer.             | File/render work can be isolated.      |

Do not use `to_thread` just because a function is slow. First ask whether it is
blocking IO, CPU-heavy work, or code that should be refactored into a pure helper
and tested directly.

## Event loop

The event loop is the scheduler that drives async functions. A top-level command
usually starts async work with a helper such as `asyncio.run(...)`. Inside async
code, do not call `asyncio.run` again; use `await`.

Top-level sync boundary:

```python
asyncio.run(run_pipeline(command))
```

Inside async code:

```python
state = await platform.run(state)
```

Calling `asyncio.run` from inside an already-running event loop is an error.

## Async design in this repository

The project uses async at orchestration boundaries and keeps math mostly
synchronous:

| Code area                | Async?    | Why                                                                         |
| ------------------------ | --------- | --------------------------------------------------------------------------- |
| Platform pipeline stages | Yes       | Stages may fetch data or run services.                                      |
| Services                 | Yes       | Services may call providers, runners, or blocking work through `to_thread`. |
| Technology adapters      | Often yes | Adapters may wrap external systems.                                         |
| Scoring math             | No        | Pure calculation is simpler synchronously.                                  |
| Statistics formulas      | No        | Pure calculations are deterministic and easy to test.                       |
| CLI parser setup         | No        | Argument parsing is local and immediate.                                    |

This split keeps the code understandable. Async is used where waiting can
overlap. Plain functions are used where values can be computed immediately.

## Common async mistakes

| Mistake                                       | Symptom                                               | Fix                                                             |
| --------------------------------------------- | ----------------------------------------------------- | --------------------------------------------------------------- |
| Forgetting `await`.                           | You see a coroutine object instead of a result.       | Add `await` at the call site.                                   |
| Calling `asyncio.run` inside async code.      | Runtime error about an active event loop.             | Use `await` instead.                                            |
| Letting one gathered task raise unexpectedly. | A whole batch fails.                                  | Catch inside the per-task wrapper if partial results are valid. |
| Blocking inside async code.                   | Other async work stalls.                              | Use an async API or `asyncio.to_thread`.                        |
| Making pure math async.                       | Tests and callers become more complex for no benefit. | Keep pure calculations synchronous.                             |

## Exceptions

Exceptions represent errors:

```python
try:
    output = await tech.execute(data)
except Exception as exc:
    return TechResult(tech_name=tech.name, output=None, success=False, error=str(exc))
```

This repository catches exceptions at service and technology boundaries so one
provider failure does not crash the whole research run.

Guidelines:

| Situation                                  | What to do                                                           |
| ------------------------------------------ | -------------------------------------------------------------------- |
| Invalid programmer input in a pure helper. | Let it raise or raise a clear exception.                             |
| Optional provider fails.                   | Catch at the adapter/service boundary and return structured failure. |
| Missing config or secret.                  | Report unavailable provider rather than making a bad call.           |
| Test expects failure.                      | Assert the exception or failed result explicitly.                    |

Avoid broad `except Exception` deep inside pure logic. It can hide real bugs.

## Filesystem paths with `Path`

Use `pathlib.Path` for paths:

```python
from pathlib import Path

data_dir = Path("~/.social-research-probe").expanduser()
report = data_dir / "reports" / "report.html"
```

The `/` operator joins paths. This is clearer and safer than string
concatenation.

Common methods:

| Method                                    | Meaning                                 |
| ----------------------------------------- | --------------------------------------- |
| `path.exists()`                           | Does this path exist?                   |
| `path.mkdir(parents=True, exist_ok=True)` | Create a directory and missing parents. |
| `path.read_text(encoding="utf-8")`        | Read a text file.                       |
| `path.write_text(text, encoding="utf-8")` | Write a text file.                      |
| `path.name`                               | Final filename.                         |
| `path.parent`                             | Parent directory.                       |

## JSON

JSON is a text format for structured data. Python dictionaries and lists map
naturally to JSON:

```python
import json

payload = {"topics": ["AI agents"]}
text = json.dumps(payload, indent=2, sort_keys=True)
loaded = json.loads(text)
```

This project uses JSON for topics, purposes, pending suggestions, cached values,
packets, and tests.

Use `sort_keys=True` when deterministic output matters. Deterministic output is
easier to diff and test.

## TOML

TOML is used for configuration:

```toml
[llm]
runner = "gemini"
```

Python reads TOML into dictionaries. The project merges default config with the
user's `config.toml`, then reads secrets separately.

Use config for behavior that should be user controlled. Do not hard-code a value
inside a service if users need to change it.

## Environment variables

Environment variables are process-level settings:

```bash
SRP_DATA_DIR=./.skill-data srp config path
```

Python reads them through `os.environ`. This project uses environment variables
for data directory overrides, secrets, and test controls such as
`SRP_DISABLE_CACHE`.

Environment variables are useful for CI and temporary shells because they do not
require writing a config file.

## Subprocesses

A subprocess runs an external command:

```python
import subprocess

result = subprocess.run(
    ["python", "-m", "social_research_probe", "--help"],
    capture_output=True,
    text=True,
    timeout=10,
)
```

This repository uses subprocesses for runner CLIs, text-to-speech tools, and
integration tests of the CLI.

Best practices:

| Practice                     | Why                                     |
| ---------------------------- | --------------------------------------- |
| Pass argv as a list.         | Avoids shell quoting problems.          |
| Use `timeout`.               | Prevents hung external commands.        |
| Capture output when testing. | Lets tests assert stdout/stderr.        |
| Handle `FileNotFoundError`.  | External binaries may not be installed. |

## Generators and comprehensions

A generator produces values lazily:

```python
(service.execute_one(item) for item in items)
```

This is used with `asyncio.gather` and other functions that can consume an
iterable.

List comprehensions create lists immediately:

```python
captions = [result.caption for result in results if result.caption]
```

Use a list comprehension when you need the final list. Use a generator when the
consumer can iterate without storing everything first.

## Sorting and keys

Python can sort values:

```python
items = sorted(items, key=lambda item: item["scores"]["overall"], reverse=True)
```

`lambda item: item["scores"]["overall"]` is a small anonymous function used only for
sorting.

Use named functions instead of lambdas when the logic is more than one simple
expression.

## Numeric code

The statistics modules intentionally use plain Python math rather than requiring
large numeric dependencies for every operation.

Example:

```python
mean = sum(values) / len(values)
variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
```

Important operators:

| Operator | Meaning                  |
| -------- | ------------------------ |
| `+`      | Add.                     |
| `-`      | Subtract.                |
| `*`      | Multiply.                |
| `/`      | Divide and return float. |
| `//`     | Floor division.          |
| `%`      | Remainder.               |
| `**`     | Power.                   |

Always handle empty lists before dividing by `len(values)`.

## Pure functions vs IO functions

A pure function depends only on its inputs and returns a value:

```python
def views(velocity: float, age_days: float) -> float:
    return velocity * age_days
```

An IO function talks to the outside world:

```python
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
```

Keep pure logic separate from IO. Pure functions are easier to test, cache, and
reuse. IO functions need more error handling because files, networks, and
subprocesses can fail.

## Services and technologies

This repository separates orchestration from concrete work.

| Concept    | Meaning                                                                                       |
| ---------- | --------------------------------------------------------------------------------------------- |
| Platform   | Owns source-specific stage order and maps platform data into shared pipeline state.           |
| Stage      | Reads and writes `PipelineState` for one named step such as `summary`, `claims`, or `report`. |
| Service    | Coordinates one task and normalizes success, skipped work, and failures.                      |
| Technology | Performs one concrete operation, provider call, renderer call, or algorithm.                  |

Services inherit from `BaseService`. A service subclass sets `service_name`,
sets `enabled_config_key`, returns technology instances from `_get_technologies`,
and implements `execute_service`.

```python
from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult


class ExampleService(BaseService[dict, dict]):
    service_name: ClassVar[str] = "youtube.example"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.example"

    def _get_technologies(self) -> list[object]:
        return [ExampleTechnology()]

    async def execute_service(self, data: dict, result: ServiceResult) -> ServiceResult:
        ...
```

Do not override `execute_batch` or `execute_one` in a service subclass. The base
class owns those methods so all services share the same disabled-service
behavior, concurrent execution, timing logs, and per-technology error isolation.
If a service has no technology layer, `_get_technologies()` returns `[None]` and
`execute_service()` performs the work directly.

Technologies inherit from `BaseTechnology`. A technology subclass sets `name`,
`health_check_key`, and `enabled_config_key`, then implements `_execute`.

```python
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class ExampleTechnology(BaseTechnology[dict, dict]):
    name: ClassVar[str] = "example"
    health_check_key: ClassVar[str] = "example"
    enabled_config_key: ClassVar[str] = "example"

    async def _execute(self, data: dict) -> dict:
        return {"ok": True, "input": data}
```

The base technology checks `[technologies]`, applies cache rules when
`cacheable` is true, times the call, catches provider errors, and returns
`None` when the adapter is disabled or fails.

Why not put everything in one function: one large function is hard to test and
hard to extend. Services and technologies keep failure boundaries clear: stages
decide order, services decide coordination, and technologies decide concrete
provider or algorithm behavior.

## Config gates

Many services and technologies have an `enabled_config_key`:

```python
enabled_config_key: ClassVar[str] = "services.youtube.analyzing.charts"
```

For services, the full dotted key documents ownership, while
`Config.service_enabled()` currently checks the final leaf name. For example,
`services.youtube.reporting.html` maps to the `html` service flag.

Technology keys are flat leaves under `[technologies]`:

```python
enabled_config_key: ClassVar[str] = "youtube_comments"
```

This lets users disable expensive or unavailable work without editing code.
Stage gates under `[stages.youtube]` sit above service and technology gates. If
`stages.youtube.comments = false`, the comments stage does not run even if
`services.youtube.enriching.comments` and `technologies.youtube_comments` are
true.

When adding a provider or service, add a clear config key and document what it
controls in `config.toml.example`, [Configuration](configuration.md), and the
skill reference.

## Caching

Technology caching stores outputs so repeated runs can reuse work:

```python
cached = get_json(cache, key)
if cached is not None:
    return cached
result = compute()
set_json(cache, key, result)
return result
```

`BaseTechnology` writes cache files below `cache/technologies/<technology-name>`
inside the active data directory. Cache entries include the input representation
and the output. Technologies that write local files or perform intentionally
fresh work should set `cacheable = False`.

Cache keys must represent the input that affects the output. If the key is too
broad, stale data can be reused incorrectly. If the key is too narrow, the cache
will miss too often.

The environment variable `SRP_DISABLE_CACHE=1` bypasses technology cache reads
and writes for the process. Tests often use this when they need to prove that a
real code path executes.

## Testing with pytest

Tests are Python functions whose names usually start with `test_`:

```python
def test_views_are_derived_from_velocity_and_age():
    assert views(10.0, 3.0) == 30.0
```

`assert` checks that something is true. If it is false, the test fails.

Pytest fixtures provide reusable test setup:

```python
def test_config_path(tmp_path):
    data_dir = tmp_path / "data"
    ...
```

`tmp_path` is a pytest fixture that gives a temporary directory.

## Monkeypatching in tests

`monkeypatch` temporarily changes environment variables, attributes, or paths:

```python
def test_uses_data_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
```

Use monkeypatch when the code reads global state such as environment variables.
The change is undone after the test.

## Mocking and fakes

A fake is a small deterministic implementation used for tests. The repository
uses fake platform and fake corroboration modules so tests do not need live
network calls.

Prefer fakes when testing pipeline behavior. Use mocks when you need to assert a
specific function was called. Avoid live APIs in normal tests because they are
slow, costly, and unstable.

## CLI parsing

The CLI uses parser modules to turn command-line arguments into structured
command objects. That means command handlers should receive already-parsed data
instead of manually reading `sys.argv`.

Example command shape:

```bash
srp research youtube "AI agents" "latest-news,trends"
```

The parser identifies the command, platform, topic, purposes, and flags. The
handler should focus on behavior.

## Common repository patterns

| Pattern            | What it looks like                                              | Why it is used                         |
| ------------------ | --------------------------------------------------------------- | -------------------------------------- |
| Small pure helper  | `def _numeric_series(...): ...`                                 | Easy to test and reason about.         |
| Service class      | `class StatisticsService(BaseService)` with `execute_service()` | Shared execution and failure behavior. |
| Technology adapter | `class GeminiRunner(...)` or `class YouTubeCommentsTech(...)`   | Isolates external tool behavior.       |
| Dataclass record   | `@dataclass class PipelineState`                                | Makes structured data explicit.        |
| Config key         | `enabled_config_key = "..."`                                    | Lets users disable behavior.           |
| Cache wrapper      | `get_json` / `set_json` under `cache/technologies/*`            | Avoids repeated expensive work.        |
| Fake in tests      | `tests/fixtures/fake_youtube.py`                                | Keeps tests deterministic.             |

## How to read a new file

Use this process when opening a Python file in this project:

1. Read the imports to see which layer it depends on.
2. Read module constants near the top.
3. Find dataclasses or classes to understand the main data shape.
4. Find public functions or methods that do the work.
5. Read private helpers after you know who calls them.
6. Find tests for the same module or behavior.

Private helpers usually start with `_`, such as `_compute`. That is a convention
meaning "internal to this module or class." Python does not strictly prevent
other code from calling it, but contributors should treat it as internal.

## How to make a safe change

| Change type      | Best first step                                     |
| ---------------- | --------------------------------------------------- |
| Pure calculation | Add or update a unit test around the function.      |
| Service behavior | Test success, disabled config, and failure output.  |
| Provider adapter | Test parsing and unavailable-provider behavior.     |
| CLI output       | Test command input and exact expected stdout shape. |
| Docs or diagrams | Run docs contract tests.                            |

Keep edits near the behavior being changed. Do not move code across layers just
because it is convenient for one call site.

## Common beginner mistakes

| Mistake                                   | Why it hurts                                         | Better approach                            |
| ----------------------------------------- | ---------------------------------------------------- | ------------------------------------------ | ------------- |
| Using a mutable default like `items=[]`.  | The same list can be reused across calls.            | Use `items: list                           | None = None`. |
| Catching every exception too early.       | Real bugs become silent empty output.                | Catch at service/provider boundaries.      |
| Building paths with string concatenation. | Breaks across platforms and edge cases.              | Use `Path` and `/`.                        |
| Calling external APIs during import.      | Tests and imports become slow or flaky.              | Call APIs inside explicit functions.       |
| Returning inconsistent dictionaries.      | Later stages fail or need defensive code everywhere. | Use dataclasses or documented dict shapes. |
| Adding provider logic to services.        | Vendor details leak into orchestration.              | Put provider specifics in technologies.    |

## Minimal example in project style

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChartRequest:
    title: str
    values: list[float]
    output_dir: Path


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def chart_caption(request: ChartRequest) -> str:
    mean = average(request.values)
    return f"{request.title}: mean value {mean:.4f}"
```

This example uses concepts from the codebase:

| Concept                  | Where it appears                   |
| ------------------------ | ---------------------------------- |
| `dataclass(frozen=True)` | Structured immutable request data. |
| `Path`                   | Filesystem output directory.       |
| `list[float]`            | Numeric series.                    |
| Empty-list guard         | Prevents division by zero.         |
| Small pure functions     | Easy unit tests.                   |
| f-string formatting      | Human-readable caption.            |

If you can understand this example, you can start reading the service,
statistics, chart, and reporting modules in this repository.
