# Design Patterns

[Home](README.md) → Design Patterns

This document explains every design pattern used in the codebase: what problem it solves, why it was the right choice here, and what the alternative would have looked like.

---

## Adapter Pattern

**Files:** `platforms/base.py`, `platforms/registry.py`, `platforms/youtube/`

### What it is

The `PlatformAdapter` protocol defines three methods — `search`, `enrich`, and `health_check` — without saying anything about which platform is on the other side. The YouTube implementation wraps the Google API behind this interface. The orchestrator never imports YouTube code directly; it asks the registry for an adapter by name and calls the interface.

### Why it was used

Without this pattern, every pipeline function would contain YouTube-specific logic. Adding a second platform (Reddit, Twitter/X, podcasts) would require forking or duplicating the orchestrator. With the adapter in place, adding a platform is a two-step operation: implement the interface, register the name.

### Why not a simpler approach

The simplest alternative would be to pass the platform name as a string and `if platform == "youtube": ...` branch everywhere. That works for one platform. By the time you add a second, you have duplicate logic in every stage function. The adapter makes the platform boundary explicit and enforces it with the type checker.

### The tradeoff

Adapters add one layer of indirection. If you never add a second platform, the interface is overhead that buys nothing. It was included here because the data model (YouTube video metadata) is not generic and the effort to abstract it would have been wasted if the project stays YouTube-only. The bet is that the overhead is small enough to justify the extensibility.

### In code

```python
# social_research_probe/platforms/base.py
from abc import ABC, abstractmethod

class PlatformAdapter(ABC):
    name: str
    default_limits: FetchLimits

    @abstractmethod
    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]: ...
    @abstractmethod
    async def enrich(self, items: list[RawItem]) -> list[RawItem]: ...
    @abstractmethod
    def health_check(self) -> bool: ...

# social_research_probe/platforms/youtube/adapter.py
@register
class YouTubeAdapter(PlatformAdapter):
    name = "youtube"
    default_limits = FetchLimits(max_items=20, recency_days=90)

    def search(self, topic, limits):
        ...   # hits YouTube Data API v3, returns list[RawItem]
```

See [Python Language Guide — Protocols](python-language-guide.md#2-protocols) for why we use an ABC instead of a `Protocol` here.

![Adapter pattern diagram](diagrams/dp_adapter.svg)

---

## Registry Pattern

**Files:** `platforms/registry.py`, `corroboration/registry.py`, `purposes/registry.py`, `llm/registry.py`

### What it is

Each subsystem keeps a dict that maps a string name to a class or factory. Callers use `get_adapter("youtube")`, `get_backend("exa")`, or `get_runner("claude")`. The registry is populated at import time; no external service discovery is involved.

### Why it was used

The orchestrator needs to resolve a platform or backend from a name that comes from the config file, not from the code. Without a registry, every call site would need a giant `if/elif` chain or importlib hacks to map strings to implementations. The registry centralises that mapping and makes it statically analysable.

### Why not a simpler approach

For a single platform with no config, a direct import is simpler: `from .youtube import YouTubeAdapter`. But `srp` lets operators choose their corroboration backend and LLM runner via `config.toml`. The name-to-class resolution must happen at runtime from a config value, which is exactly what registries are for.

### The tradeoff

Registries hide which implementations are available — you can't see them by reading a single file. The registry files themselves (`registry.py`) are the single source of truth and are kept small to mitigate this.

### In code

```python
# social_research_probe/llm/registry.py
_REGISTRY: dict[str, type[LLMRunner]] = {}

def register(cls: type[LLMRunner]) -> type[LLMRunner]:
    _REGISTRY[cls.name] = cls
    return cls

def get_runner(name: str) -> LLMRunner:
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        raise ValidationError(f"unknown runner: {name}") from exc

# social_research_probe/llm/runners/gemini.py
@register
class GeminiRunner(LLMRunner):
    name = "gemini"
    ...
```

The same pattern is used by [`platforms/registry.py`](../social_research_probe/platforms/registry.py), [`corroboration/registry.py`](../social_research_probe/corroboration/registry.py), and [`purposes/registry.py`](../social_research_probe/purposes/registry.py).

![Registry pattern diagram](diagrams/dp_registry.svg)

---

## Strategy Pattern

**Files:** `corroboration/host.py`, `llm/ensemble.py`, `pipeline/orchestrator.py`

### What it is

A strategy is a pluggable behaviour that can be swapped at runtime without changing the code that uses it. In `srp`:

- The corroboration strategy is selected by `Config.corroboration_backend`: `host` discovers all available backends; `exa` forces one; `none` disables corroboration entirely.
- The LLM ensemble is a strategy set: all configured runners are called concurrently and the first successful result wins.

### Why it was used

Corroboration backends and LLM runners have identical call signatures but completely different implementations (different APIs, different authentication, different rate limits). The strategy pattern lets the orchestrator say "corroborate this claim" without knowing or caring which service does the work.

### Why not a simpler approach

You could hard-code Exa as the only corroboration backend and remove the selection logic entirely. That would work — until an operator's Exa trial expires and they need Brave instead. The strategy pattern makes backend substitution a config change, not a code change.

### The tradeoff

Strategy selection adds a runtime dispatch step and makes it harder to trace "what actually runs" from reading the code alone. The config file is now part of understanding the execution path, which is an operational cost.

### In code

```python
# social_research_probe/pipeline/orchestrator.py — simplified
def _available_backends(config: Config) -> list[CorroborationBackend]:
    choice = config.corroboration_backend
    if choice == "none":
        return []
    if choice == "host":
        # Try every registered backend; keep the healthy ones.
        return [b for b in (get_backend(n) for n in list_backends()) if b.health_check()]
    backend = get_backend(choice)
    return [backend] if backend.health_check() else []
```

The orchestrator never names a specific backend — it asks for "the configured strategy" and works with whatever comes back. Adding a new backend means only editing the registry, not the orchestrator.

![Strategy pattern diagram](diagrams/dp_strategy.svg)

---

## Pipeline / Chain-of-Steps

**Files:** `pipeline/orchestrator.py` and its submodules

### What it is

The research pipeline is a fixed sequence of stages: adapter setup → score → enrich → stats → charts → corroborate → synthesise. Each stage is implemented in its own submodule (`scoring.py`, `enrichment.py`, `stats.py`, `charts.py`, `corroboration.py`, `svs.py`). The orchestrator calls them in order, passing the packet forward.

### Why it was used

The research process has a natural linear dependency: you cannot enrich items you haven't scored yet; you cannot corroborate claims you haven't identified yet. Encoding the sequence explicitly makes the data dependencies visible and prevents stages from accidentally running out of order.

### Why not a dynamic pipeline

A dynamic pipeline would let you register stages in any order, skip stages via config, or inject custom stages. That flexibility is useful for a general-purpose framework, not for a tool with a single well-defined research workflow. A dynamic pipeline would make the execution order invisible in the code — exactly the opposite of what an evidence-first tool should do.

### The tradeoff

The fixed sequence is inflexible. If a future use case needs to run corroboration before enrichment (to filter low-credibility items before spending LLM budget), the orchestrator would need refactoring. For now, the simplicity of "read top-to-bottom and you understand the whole pipeline" is the right tradeoff.

### In code

```python
# social_research_probe/pipeline/orchestrator.py — stage chain
async def run_research(cmd: ParsedRunResearch, config: Config) -> ResearchPacket:
    adapter = get_adapter(cmd.platform, config)
    raw     = adapter.search(cmd.topic, adapter.default_limits)
    items   = await adapter.enrich(raw)
    scored  = sorted((_score_item(i, config) for i in items), reverse=True)
    top_n   = scored[: config.enrich_top_n]
    summaries = await _enrich_top5_with_transcripts(top_n, config)
    evidence  = await _corroborate_top5(top_n, _available_backends(config))
    stats     = _build_stats_summary(scored)
    charts    = _render_charts(scored, stats)
    return build_packet(cmd, scored, summaries, evidence, stats, charts)
```

Read top-to-bottom and you have the whole tool.

![Pipeline pattern diagram](diagrams/dp_pipeline.svg)

---

## Command Object

**Files:** `commands/parse.py`

### What it is

`ParsedRunResearch` is a typed dataclass built from the raw `argparse.Namespace`. The CLI creates it; the orchestrator consumes it. The CLI knows nothing about what the orchestrator does with the command; the orchestrator knows nothing about argparse.

### Why it was used

Without this separation, the orchestrator's function signature would be `run_research(args: argparse.Namespace, ...)`. That couples the orchestrator to argparse internals — attribute names, optional types, defaults. Tests would need to construct `argparse.Namespace` objects with the right fields, which is fragile. With a typed command object, the orchestrator can be tested by constructing a plain dataclass.

### Why not just pass the namespace directly

`argparse.Namespace` has no type annotations. You cannot know from the type signature alone which fields are present or what types they have. Any typo in an attribute name becomes a runtime `AttributeError`. The command object makes the contract explicit and type-checkable.

### The tradeoff

You now have two representations of the same data — `Namespace` and `ParsedRunResearch` — and conversion code between them. This is a small but real maintenance cost: when you add a CLI flag you must also update the command object and the parsing function.

### In code

```python
# social_research_probe/commands/parse.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ParsedRunResearch:
    platform: str
    topic: str
    purposes: tuple[str, ...]
    no_shorts: bool = False
    no_transcripts: bool = False
    no_html: bool = False

def parse_run_research(ns: argparse.Namespace) -> ParsedRunResearch:
    platform, topic, purposes = _split_positional(ns.args)
    return ParsedRunResearch(
        platform=platform, topic=topic, purposes=purposes,
        no_shorts=ns.no_shorts, no_transcripts=ns.no_transcripts, no_html=ns.no_html,
    )
```

See [Python Language Guide — Dataclasses vs TypedDicts](python-language-guide.md#11-dataclasses-vs-typeddicts) for when to pick each.

---

## Builder

**Files:** `synthesize/formatter.py`

### What it is

`build_packet` assembles a `ResearchPacket` dict from all the outputs of the pipeline stages: scored items, evidence snippets, signal summaries, statistical highlights, chart paths, and warnings. It is the single place where the packet is constructed. No other code creates `ResearchPacket` dicts directly.

### Why it was used

Without a builder, each pipeline stage would be responsible for populating part of the packet. Callers would need to know which keys exist, which are optional, and what format each field takes. With a builder, callers hand over data and get back a complete, validated packet.

### Why not just use a dict literal

A plain dict literal works fine at first. The problem surfaces when you need to add a new field — you have to find every dict literal in the codebase and update each one. With a single `build_packet` function, the packet structure is defined in one place and all callers update automatically.

### The tradeoff

The builder function is the biggest function in `synthesize/`. As the packet format grows, the builder grows with it. Watch for it approaching the 50-line limit (defined in project rules) — at that point it should be decomposed into sub-builders per section.

### In code

```python
# social_research_probe/synthesize/formatter.py — sketch
def build_packet(
    cmd: ParsedRunResearch,
    scored: list[ScoredItem],
    summaries: dict[str, str],
    evidence: dict[str, list[Evidence]],
    stats: StatsSummary,
    charts: ChartPaths,
) -> ResearchPacket:
    packet: ResearchPacket = {
        "query": {"platform": cmd.platform, "topic": cmd.topic},
        "items_top5": _attach(scored[:5], summaries, evidence),
        "stats": stats,
        "chart_captions": charts,
        "warnings": [],
    }
    return packet
```

Every stage hands raw data to the builder; no stage writes packet keys directly.

---

## Fake-via-Environment Test Seam

**Files:** `pipeline/orchestrator.py`, `tests/fixtures/fake_youtube.py`

### What it is

Setting `SRP_TEST_USE_FAKE_YOUTUBE=1` before a test causes `_maybe_register_fake()` — called at the top of `run_research` — to import and register a fake YouTube adapter. No production code is mocked; the fake implements the real `PlatformAdapter` interface and goes through the same call path as the real adapter.

### Why it was used

Integration tests need to exercise the full pipeline without making real YouTube API calls. The alternatives are:

1. **Mock the adapter at the call site** — fragile; if the orchestrator's internal code changes (e.g. switches from `adapter.search()` to `adapter.find()`), the mock silently stops testing the right thing.
2. **Dependency injection** — pass the adapter as a parameter to `run_research`. Clean but requires changing every call site, including the CLI.
3. **Environment-based seam** — the fake is registered via a side-effectful import triggered by an env var, leaving the call site and the orchestrator signature unchanged.

The env-based seam was chosen because it adds zero production complexity and lets the integration tests exercise exactly the same code path as a real run.

### Why not mock

Mocks test that the code *calls* the right method with the right arguments. Fakes test that the code *works correctly* end-to-end. For a pipeline where the stages are tightly coupled, fakes give much stronger assurance.

### The tradeoff

The env-based seam is invisible in the code — there is no import statement to follow. A reader unfamiliar with the pattern may not realise the fake is registered. The `_maybe_register_fake` function makes this explicit; the comment in `conftest.py` explains the convention to new contributors.

### In code

```python
# social_research_probe/pipeline/orchestrator.py
def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        from tests.fixtures.fake_youtube import FakeYouTubeAdapter
        _platforms_registry.register(FakeYouTubeAdapter)

async def run_research(cmd, config):
    _maybe_register_fake()
    adapter = get_adapter(cmd.platform, config)
    ...
```

The production call site is unchanged; only the registry entry differs. Tests set `SRP_TEST_USE_FAKE_YOUTUBE=1` and exercise the real orchestrator end-to-end against a fake that implements the same protocol.

![Fake-via-environment test seam diagram](diagrams/dp_fake_seam.svg)

---

## Soft Failure / Degraded Mode

**Files:** `synthesize/warnings.py`, `pipeline/orchestrator.py`

### What it is

When an optional stage fails — a corroboration backend is unreachable, a transcript cannot be fetched, an LLM call times out — the pipeline does not raise an exception and abort. It attaches a `skip_reason` or a warning to the affected item, continues to the next stage, and surfaces the issue in section 9 (Warnings) of the report.

### Why it was used

`srp` depends on at least four external services (YouTube API, LLM runner, and one or more corroboration APIs). Any of them can fail, rate-limit, or be unconfigured. Treating any failure as fatal would make the tool unusable in practice. Soft failure lets operators get a partial result and understand exactly what was skipped and why.

### Why not fail fast

Fail-fast is the right choice when partial results are worse than no result — for example, a financial transaction that is half-applied. A research report with some sections missing is still useful; an aborted run produces nothing. The design matches the use case.

### The tradeoff

Soft failures can hide configuration problems. An operator who has not set up corroboration keys may not notice the warning buried in section 9. The check-secrets command exists specifically to surface this before a run; the installation guide (see [Installation](installation.md)) walks through verifying your setup.

### In code

```python
# social_research_probe/pipeline/orchestrator.py — corroboration step
async def _corroborate_top5(items, backends, warnings):
    for backend in backends:
        try:
            return await backend.check_claims(items)
        except Exception as exc:
            warnings.append(f"corroboration backend '{backend.name}' failed: {exc}")
            continue
    warnings.append("corroboration skipped — no healthy backend")
    return {}
```

The pipeline continues with an empty result rather than aborting. The failure appears in section 9 of the report so it is never silently lost.

---

## Separation of Concerns

**Files:** `cli/`, `commands/`, `pipeline/`, `synthesize/`

### What it is

The codebase is split into layers with strict boundaries: CLI handles arguments and output; commands holds typed value objects; pipeline orchestrates and calls adapters; synthesize formats results. No layer imports from a layer above it.

### Why it was used

Without layer boundaries, it is easy to let CLI parsing logic leak into the orchestrator ("if the user passed `--no-shorts`, skip shorts") or to let the orchestrator emit progress messages directly to stdout. These leaks make each component harder to test in isolation and harder to reuse.

### Why not a flat structure

A flat structure (`cli.py` doing everything) is simpler for small scripts. `srp` crossed the threshold where a flat structure became hard to navigate — `cli.py` and `pipeline.py` each exceeded 600 lines before the split. Separation by layer was the refactor that brought them back under the 500-line project limit.

### The tradeoff

More files to navigate. A new contributor needs to understand the layer model before they can add a feature. The [Architecture doc](architecture.md) exists to explain this model upfront.

### In code

```python
# Import direction (enforced by convention + ./.venv/bin/ruff rules):
#   cli/       → commands/, config, errors           (reads user input)
#   commands/  → config, errors, types               (typed value objects)
#   pipeline/  → platforms/, llm/, corroboration/,   (pure orchestration)
#                stats/, viz/, synthesize/
#   synthesize/→ types                               (no side effects)
#
# What is NOT allowed:
#   pipeline/  →  cli/       # pipeline must not print
#   platforms/ →  pipeline/  # adapters must not drive the pipeline
```

`ruff`'s import-ordering rules plus the small number of layers make violations easy to spot in review.

---

## See also

- [Architecture](architecture.md) — module map and how the patterns fit together
- [Testing](testing.md) — how fakes and test seams are exercised
- [Python Language Guide](python-language-guide.md) — language conventions (Protocols, TypedDicts) that enable these patterns
