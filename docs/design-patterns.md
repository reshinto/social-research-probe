# Design Patterns

[Home](README.md) → Design Patterns

This document describes the patterns used in the codebase. Each pattern entry names the files where it appears and explains why it was chosen.

---

## Adapter Pattern

**Files:** `platforms/base.py`, `platforms/registry.py`, `platforms/youtube/`

`PlatformAdapter` defines the interface (`search`, `enrich`, `health_check`). The YouTube implementation wraps the YouTube Data API v3 behind this interface. New platforms implement the same contract without touching the orchestrator.

The `get_adapter(platform_name)` function in `registry.py` resolves the adapter at runtime, keeping the orchestrator decoupled from any specific platform.

---

## Registry Pattern

**Files:** `platforms/registry.py`, `corroboration/registry.py`, `purposes/registry.py`, `llm/registry.py`

Each subsystem maintains a registry that maps string names to implementations. Callers use `get_backend("exa")` or `get_runner("claude")` — no direct imports of concrete classes.

This makes adding a new backend a two-step operation: implement the class, register it. The orchestrator and CLI do not need to change.

---

## Strategy Pattern

**Files:** `corroboration/host.py`, `llm/ensemble.py`

`_available_backends` in `pipeline/orchestrator.py` selects corroboration strategies at runtime based on `Config.corroboration_backend`. The `host` strategy auto-discovers strategies by running each backend's `health_check()`; specific strategies bypass discovery.

In `llm/ensemble.py`, each LLM runner is a strategy. The ensemble fans out to all configured runners and returns the first successful result.

---

## Pipeline / Chain-of-Steps

**Files:** `pipeline/orchestrator.py`

The orchestrator runs a fixed sequence: adapter setup → enrich query → search → enrich items → score → top-5 → corroborate → stats → charts → packet assembly. Each step is a focused function in its own submodule (`scoring.py`, `enrichment.py`, `stats.py`, `charts.py`, `corroboration.py`, `svs.py`).

The pipeline is explicit rather than dynamic — there is no step registry or plugin system, because the step order is invariant.

---

## Command Object

**Files:** `commands/parse.py`

`ParsedRunResearch` is a typed dataclass built from the raw `argparse.Namespace`. The CLI creates the command object; the orchestrator consumes it. This separates argument-parsing logic from pipeline logic and makes the pipeline independently testable.

---

## Builder

**Files:** `synthesize/formatter.py`

`build_packet` assembles a `ResearchPacket` by collecting scored items, evidence snippets, statistical summaries, and chart captions into a single serialisable dict. It is called once at the end of the pipeline — callers never construct packets directly.

---

## Composition over Inheritance

**Files:** `platforms/youtube/adapter.py`, `corroboration/base.py`

Adapters and backends receive configuration as plain dicts (`AdapterConfig`) rather than inheriting from a base class that provides configuration. This avoids deep class hierarchies and makes each implementation independently understandable.

---

## Health-Check Protocol

**Files:** `platforms/base.py`, `corroboration/base.py`

Both `PlatformAdapter` and `CorroborationBackend` expose a `health_check() -> bool` method. The orchestrator calls health checks before committing to a platform or backend, and degrades gracefully (skipping unavailable backends, surfacing a warning) rather than failing.

---

## Fake-via-Environment Test Seam

**Files:** `pipeline/orchestrator.py`, `tests/fixtures/fake_youtube.py`

Setting `SRP_TEST_USE_FAKE_YOUTUBE=1` causes `_maybe_register_fake()` to import and register a fake YouTube adapter before the orchestrator runs. No production code is mocked; the fake implements the real adapter interface and is exercised by the integration tests.

The same pattern applies to corroboration backends via `SRP_TEST_USE_FAKE_CORROBORATION=1`.

---

## Soft Failure / Degraded Mode

**Files:** `synthesize/warnings.py`, `pipeline/orchestrator.py`

When a corroboration backend is unavailable, the pipeline attaches a `skip_reason` to the affected items rather than raising. `detect_warnings` collects these signals and surfaces them in the report. The run succeeds with a degraded result rather than failing.

---

## Separation of Concerns

**Files:** `cli/`, `commands/`, `pipeline/`, `synthesize/`

The CLI layer handles argument parsing, output formatting, and error surfacing. It does not contain pipeline logic. The pipeline layer does not know about argparse or report formats. The synthesis layer does not call platform APIs. This strict layering means each layer can be tested and reasoned about independently.

---

## See also

- [Architecture](architecture.md) — module map and data flow
- [Testing](testing.md) — how the patterns are exercised in tests
- [Python Language Guide](python-language-guide.md) — language conventions that support these patterns
