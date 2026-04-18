# SocialResearchProbe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `srp` — a Python CLI + Claude Code skill for evidence-first YouTube social-media research with mode-aware LLM routing (skill mode redirects to host LLM via JSON packet; CLI mode subprocesses LLM CLI binaries).

**Architecture:** Single installable Python package (`social_research_probe`) with internal registries for platforms, LLM runners, and corroboration backends. `srp --mode skill` emits a compact JSON packet to stdout for the host LLM to finalize; `srp --mode cli` shells out to `claude`/`gemini`/`codex`/`ollama`. All deterministic logic — parsing, scoring, deduplication, migration — runs in pure Python with zero LLM involvement.

**Tech Stack:** Python 3.11+, argparse (CLI), jsonschema (state validation), rapidfuzz (dedupe), google-api-python-client (YouTube Data API v3), yt-dlp (transcripts, lazy), numpy/scipy/statsmodels (stats, P3), matplotlib (viz, P3), pytest + pytest-cov + ruff (tooling). No Anthropic/OpenAI/Google LLM SDKs ever (Hard Invariant #2).

---

## Scope Note

This plan covers **P0 (Scaffold)**, **P1 (State + Commands + Config/Secrets)**, and **P2 (YouTube Adapter + Pipeline Shell + Skill-mode Output)**. These three phases together produce the first working end-to-end deliverable:

```
srp run-research --mode skill --platform youtube '"ai agents"->trends'
```

emits a valid `SkillPacket` JSON to stdout (sections 1–9 populated; 10–11 left to the host LLM per `references/run-research.md`).

**Follow-on plans (not covered here):**
- **P3:** stats + viz (sections 8–9 real)
- **P4:** reference docs complete + host-LLM suggestion enhancement path
- **P5:** CLI-mode LLM runners (`claude`, `gemini`, `codex`, `ollama`)
- **P6:** AI-slop detection + claim extraction + web corroboration (Exa/Brave/Tavily)
- **P7:** Second platform adapter
- **P8:** Perf + UX polish

---

## Conventions

- **TDD discipline:** write failing test → verify it fails → write minimal implementation → verify it passes → commit. Never batch tests and implementation.
- **Commit frequency:** each task ends with one commit. Commit messages use Conventional Commits (`feat:`, `test:`, `chore:`, `fix:`).
- **Path convention:** all file paths are relative to `/Users/springfield/dev/social-research-probe/` (project root).
- **Python version:** 3.11+ (uses `tomllib` from stdlib, PEP 604 unions, structural pattern matching).
- **Test command:** `pytest` from project root. Contract tests live in `tests/contract/`.
- **Lint command:** `ruff check src/ tests/`. Format: `ruff format src/ tests/`.
- **Zero-LLM enforcement:** a contract test greps `src/` for forbidden imports; CI fails if it finds any.

---

## File Structure Created Across P0–P2

```
social-research-probe/
├── pyproject.toml
├── README.md
├── config.toml.example
├── .gitignore
├── .github/workflows/ci.yml
├── SocialResearchProbe/
│   ├── SKILL.md
│   └── references/
│       ├── update-topics.md
│       ├── show-topics.md
│       ├── update-purposes.md
│       ├── show-purposes.md
│       ├── suggest-topics.md
│       ├── suggest-purposes.md
│       ├── show-pending.md
│       ├── apply-pending.md
│       ├── discard-pending.md
│       └── run-research.md
├── src/social_research_probe/
│   ├── __init__.py
│   ├── cli.py                    — argparse entry + subcommand dispatch
│   ├── errors.py                 — SrpError hierarchy + exit-code mapping
│   ├── config.py                 — data-dir + config.toml + secrets.toml
│   ├── dedupe.py                 — rapidfuzz duplicate detection
│   ├── pipeline.py               — run_research() (P2)
│   ├── state/
│   │   ├── __init__.py
│   │   ├── store.py              — atomic JSON read/write + seeding
│   │   ├── schemas.py            — jsonschema dicts for all state files
│   │   ├── validate.py           — validation wrapper
│   │   └── migrate.py            — version-chain migrators + backup
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── parse.py              — DSL parser (recursive-descent)
│   │   ├── topics.py             — update-topics / show-topics
│   │   ├── purposes.py           — update-purposes / show-purposes
│   │   ├── suggestions.py        — suggest-/show-pending/apply/discard
│   │   ├── config.py             — srp config subcommands
│   │   └── research.py           — run-research handler (P2)
│   ├── purposes/
│   │   ├── __init__.py
│   │   ├── registry.py           — purpose lookup helpers
│   │   └── merge.py              — MergedPurpose computation
│   ├── platforms/                — P2
│   │   ├── __init__.py
│   │   ├── base.py               — dataclasses + PlatformAdapter ABC
│   │   ├── registry.py           — @register + get_adapter
│   │   ├── signals.py            — cross-item batch signals
│   │   └── youtube/
│   │       ├── __init__.py
│   │       ├── adapter.py
│   │       ├── fetch.py
│   │       ├── extract.py
│   │       └── trust_hints.py
│   ├── validation/               — P2
│   │   ├── __init__.py
│   │   └── source.py             — primary/secondary/commentary/unknown
│   ├── scoring/                  — P2
│   │   ├── __init__.py
│   │   ├── trust.py
│   │   ├── trend.py
│   │   ├── opportunity.py
│   │   └── combine.py
│   ├── llm/                      — P2
│   │   ├── __init__.py
│   │   ├── base.py               — LLMRunner ABC (stub; populated in P5)
│   │   └── host.py               — emit_packet (skill-mode)
│   └── synthesize/               — P2
│       ├── __init__.py
│       └── formatter.py          — sections 1-9 + packet builder
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   └── fake_youtube.py       — P2
    ├── contract/
    │   ├── __init__.py
    │   └── test_no_llm_sdk.py
    ├── unit/
    │   ├── __init__.py
    │   ├── test_cli_stub.py
    │   ├── test_errors.py
    │   ├── test_config.py
    │   ├── test_state_store.py
    │   ├── test_state_schemas.py
    │   ├── test_state_migrate.py
    │   ├── test_dedupe.py
    │   ├── test_parse.py
    │   ├── test_topics.py
    │   ├── test_purposes.py
    │   ├── test_purpose_merge.py
    │   ├── test_suggestions.py
    │   ├── test_config_cmd.py
    │   ├── test_source.py
    │   ├── test_scoring.py
    │   ├── test_host_emit.py
    │   └── test_formatter.py
    └── integration/
        ├── __init__.py
        ├── test_state_cli.py
        └── test_run_research_skill.py
```

---

## Phase P0 — Scaffold

Goal: a package that installs with `pip install -e .`, exposes the `srp` console script, prints help, and enforces Hard Invariant #2 via a contract test. Zero logic.

---

### Task 1: Initialize git repo + package scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/social_research_probe/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/contract/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Initialize git + create dir tree**

```bash
cd /Users/springfield/dev/social-research-probe
git init
mkdir -p src/social_research_probe tests/unit tests/contract tests/integration tests/fixtures
touch src/social_research_probe/__init__.py tests/__init__.py tests/unit/__init__.py tests/contract/__init__.py tests/integration/__init__.py
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
.venv/
venv/
.skill-data/
.DS_Store
```

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "social-research-probe"
version = "0.1.0"
description = "Evidence-first social-media research CLI + Claude Code skill"
requires-python = ">=3.11"
readme = "README.md"
license = {text = "MIT"}
dependencies = [
    "jsonschema>=4.0",
    "rapidfuzz>=3.0",
    "google-api-python-client>=2.0",
    "yt-dlp>=2024.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "hypothesis>=6.0",
    "ruff>=0.6",
]

[project.scripts]
srp = "social_research_probe.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/social_research_probe"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
pythonpath = ["src"]

[tool.coverage.run]
source = ["src/social_research_probe"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]  # handled by formatter

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["N802"]  # allow test_SomethingLikeThis
```

- [ ] **Step 4: Write minimal `README.md`**

```markdown
# social-research-probe

Evidence-first social-media research CLI + Claude Code skill. See [design spec](docs/superpowers/specs/2026-04-18-social-research-probe-design.md).

## Install

    pip install -e '.[dev]'

## Run

    srp --help
```

- [ ] **Step 5: Write `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect SRP data dir to a per-test temp path."""
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir()
    monkeypatch.setenv("SRP_DATA_DIR", str(data_dir))
    return data_dir
```

- [ ] **Step 6: Install in editable mode + verify package loads**

```bash
pip install -e '.[dev]'
python -c "import social_research_probe; print(social_research_probe.__name__)"
```

Expected stdout: `social_research_probe`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: initial package scaffold"
```

---

### Task 2: Error hierarchy + exit codes

**Files:**
- Create: `src/social_research_probe/errors.py`
- Create: `tests/unit/test_errors.py`

- [ ] **Step 1: Write failing test `tests/unit/test_errors.py`**

```python
"""Exit codes map to the spec §9 table."""
from __future__ import annotations

import pytest

from social_research_probe.errors import (
    AdapterError,
    DuplicateError,
    MigrationError,
    SrpError,
    ValidationError,
)


def test_base_error_defaults_to_exit_2():
    err = SrpError("generic")
    assert err.exit_code == 2
    assert str(err) == "generic"


@pytest.mark.parametrize(
    ("exc_cls", "expected_code"),
    [
        (ValidationError, 2),
        (DuplicateError, 3),
        (AdapterError, 4),
        (MigrationError, 5),
    ],
)
def test_subclass_exit_codes(exc_cls: type[SrpError], expected_code: int):
    assert exc_cls("x").exit_code == expected_code
    assert issubclass(exc_cls, SrpError)
```

- [ ] **Step 2: Run — expect import failure**

```bash
pytest tests/unit/test_errors.py -v
```

Expected: `ModuleNotFoundError: No module named 'social_research_probe.errors'`

- [ ] **Step 3: Write `src/social_research_probe/errors.py`**

```python
"""Exception hierarchy. Each subclass carries its spec §9 exit code."""
from __future__ import annotations


class SrpError(Exception):
    exit_code: int = 2


class ValidationError(SrpError):
    exit_code = 2


class DuplicateError(SrpError):
    exit_code = 3


class AdapterError(SrpError):
    exit_code = 4


class MigrationError(SrpError):
    exit_code = 5
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_errors.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/errors.py tests/unit/test_errors.py
git commit -m "feat(errors): SrpError hierarchy with spec exit codes"
```

---

### Task 3: CLI stub (argparse) with --help + unknown-subcommand exit 2

**Files:**
- Create: `src/social_research_probe/cli.py`
- Create: `tests/unit/test_cli_stub.py`

- [ ] **Step 1: Write failing test `tests/unit/test_cli_stub.py`**

```python
"""CLI stub: --help works, unknown subcommand exits 2, no subcommand exits 2."""
from __future__ import annotations

import subprocess
import sys


def _run_srp(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "social_research_probe.cli", *args],
        capture_output=True,
        text=True,
    )


def test_help_exits_zero():
    result = _run_srp("--help")
    assert result.returncode == 0
    assert "srp" in result.stdout.lower()
    assert "run-research" in result.stdout or "usage" in result.stdout.lower()


def test_no_subcommand_exits_2():
    result = _run_srp()
    assert result.returncode == 2


def test_unknown_subcommand_exits_2():
    result = _run_srp("bogus-command")
    assert result.returncode == 2
```

- [ ] **Step 2: Run — expect failure (module has no `__main__` entry)**

```bash
pytest tests/unit/test_cli_stub.py -v
```

Expected: FAIL (module not runnable or returncode mismatch).

- [ ] **Step 3: Write `src/social_research_probe/cli.py`**

```python
"""CLI entry point. Subcommands are registered here and dispatched by name."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from social_research_probe.errors import SrpError

# Registry populated by subcommand modules in later tasks.
# Each entry: name -> (parser_configurator, handler)
_SUBCOMMANDS: dict[str, tuple[Callable[[argparse.ArgumentParser], None], Callable[[argparse.Namespace], int]]] = {}


def register_subcommand(
    name: str,
    configure: Callable[[argparse.ArgumentParser], None],
    handler: Callable[[argparse.Namespace], int],
) -> None:
    _SUBCOMMANDS[name] = (configure, handler)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="srp", description="Evidence-first social-media research.")
    parser.add_argument("--mode", choices=["skill", "cli"], default="cli")
    parser.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    for name, (configure, _handler) in _SUBCOMMANDS.items():
        sub = subparsers.add_parser(name)
        configure(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return 2

    _configure, handler = _SUBCOMMANDS[args.command]
    try:
        return handler(args)
    except SrpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_cli_stub.py -v
srp --help
```

Expected: 3 passed; `srp --help` prints usage, exits 0.

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/cli.py tests/unit/test_cli_stub.py
git commit -m "feat(cli): argparse stub with global flags + subcommand registry"
```

---

### Task 4: SKILL.md + 10 reference stubs

**Files:**
- Create: `SocialResearchProbe/SKILL.md`
- Create: `SocialResearchProbe/references/update-topics.md`
- Create: `SocialResearchProbe/references/show-topics.md`
- Create: `SocialResearchProbe/references/update-purposes.md`
- Create: `SocialResearchProbe/references/show-purposes.md`
- Create: `SocialResearchProbe/references/suggest-topics.md`
- Create: `SocialResearchProbe/references/suggest-purposes.md`
- Create: `SocialResearchProbe/references/show-pending.md`
- Create: `SocialResearchProbe/references/apply-pending.md`
- Create: `SocialResearchProbe/references/discard-pending.md`
- Create: `SocialResearchProbe/references/run-research.md`

- [ ] **Step 1: Create `SocialResearchProbe/SKILL.md`**

```markdown
---
name: SocialResearchProbe
description: Evidence-first social-media research via the `srp` CLI. Triggers on
  update-topics, update-purposes, show-topics, show-purposes, suggest-topics,
  suggest-purposes, show-pending-suggestions, apply-pending-suggestions,
  discard-pending-suggestions, run-research.
---

# SocialResearchProbe

Shell out to `srp`; never reimplement logic. Always pass `--mode skill` so the CLI
emits a packet instead of calling an external LLM.

## Command → reference

| User command                    | Reference file                        |
|---------------------------------|---------------------------------------|
| update-topics                   | references/update-topics.md           |
| show-topics                     | references/show-topics.md             |
| update-purposes                 | references/update-purposes.md         |
| show-purposes                   | references/show-purposes.md           |
| suggest-topics                  | references/suggest-topics.md          |
| suggest-purposes                | references/suggest-purposes.md        |
| show-pending-suggestions        | references/show-pending.md            |
| apply-pending-suggestions       | references/apply-pending.md           |
| discard-pending-suggestions     | references/discard-pending.md         |
| run-research                    | references/run-research.md            |

1. Identify the user's command.
2. Read the matching reference file.
3. Follow its instructions exactly.
4. Report CLI stdout verbatim. On non-zero exit surface stderr + exit code.
```

- [ ] **Step 2: Create 10 reference stubs (content to be filled in P4)**

Each stub file contains a single-line placeholder pointing to the future content location. Use this exact pattern for each:

`SocialResearchProbe/references/update-topics.md`:
```markdown
# update-topics

<!-- Filled in Phase P4. See spec §10 and docs/superpowers/specs/2026-04-18-social-research-probe-design.md. -->

Invoke: `srp update-topics --mode skill --add '"topic1"|"topic2"'` (or `--remove`, `--rename`).
Report stdout verbatim. On exit 3 (duplicate) surface the match details from stderr.
```

`SocialResearchProbe/references/show-topics.md`:
```markdown
# show-topics

<!-- Filled in Phase P4. -->

Invoke: `srp show-topics --mode skill --output text`. Print stdout verbatim.
```

`SocialResearchProbe/references/update-purposes.md`:
```markdown
# update-purposes

<!-- Filled in Phase P4. -->

Invoke: `srp update-purposes --mode skill --add 'name=method summary'` (or `--remove`, `--rename`).
Report stdout verbatim.
```

`SocialResearchProbe/references/show-purposes.md`:
```markdown
# show-purposes

<!-- Filled in Phase P4. -->

Invoke: `srp show-purposes --mode skill --output text`. Print stdout verbatim.
```

`SocialResearchProbe/references/suggest-topics.md`:
```markdown
# suggest-topics

<!-- Filled in Phase P4. -->

1. Invoke: `srp suggest-topics --mode skill --output json`.
2. If CLI returns a packet with `kind=suggestions`, enhance per schema and pipe back:
   `echo '<json>' | srp stage-suggestions --from-stdin`.
```

`SocialResearchProbe/references/suggest-purposes.md`:
```markdown
# suggest-purposes

<!-- Filled in Phase P4. Same pattern as suggest-topics.md. -->
```

`SocialResearchProbe/references/show-pending.md`:
```markdown
# show-pending-suggestions

<!-- Filled in Phase P4. -->

Invoke: `srp show-pending --mode skill --output text`. Print stdout verbatim.
```

`SocialResearchProbe/references/apply-pending.md`:
```markdown
# apply-pending-suggestions

<!-- Filled in Phase P4. -->

Invoke: `srp apply-pending --mode skill --topics <IDS|all> --purposes <IDS|all>`.
Report stdout. On exit 3 surface dedupe match details.
```

`SocialResearchProbe/references/discard-pending.md`:
```markdown
# discard-pending-suggestions

<!-- Filled in Phase P4. -->

Invoke: `srp discard-pending --mode skill --topics <IDS|all> --purposes <IDS|all>`.
Report stdout.
```

`SocialResearchProbe/references/run-research.md`:
```markdown
# run-research

<!-- Fully filled in Phase P4. Skeleton below is for P2 wire-up. -->

1. Pre-flight: `srp config check-secrets --needed-for run-research --platform youtube --output json`.
2. If `missing` is non-empty, instruct the user to run `srp config set-secret <name>` in their
   terminal (hidden-input prompt). Never ask the user to paste a key into chat. Stop.
3. Otherwise: `srp run-research --mode skill --platform youtube '<topics>'`.
4. Parse the emitted `SkillPacket` JSON. Fill `compiled_synthesis` (≤150 words) and
   `opportunity_analysis` (≤150 words) per the packet's `response_schema`.
5. Stitch sections 1–11 and emit to the user.
```

- [ ] **Step 3: Commit**

```bash
git add SocialResearchProbe/
git commit -m "feat(skill): minimal SKILL.md + 10 reference stubs"
```

---

### Task 5: Contract test — no LLM SDK imports

**Files:**
- Create: `tests/contract/test_no_llm_sdk.py`

- [ ] **Step 1: Write contract test**

```python
"""Hard Invariant #2: no LLM SDK imports anywhere in src/.

Rationale: the skill must never bundle a Python LLM client. Skill mode uses the
host LLM; CLI mode subprocesses external LLM CLIs. Any import of these packages
is a spec violation.
"""
from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_TOP_LEVEL = {"anthropic", "openai", "cohere"}
FORBIDDEN_DOTTED = {"google.generativeai", "google.genai"}

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "social_research_probe"

_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(?P<from_pkg>[\w.]+)\s+import\s+|import\s+(?P<import_pkg>[\w.,\s]+))",
    re.MULTILINE,
)


def _iter_imports(content: str) -> list[str]:
    imports: list[str] = []
    for match in _IMPORT_RE.finditer(content):
        if pkg := match.group("from_pkg"):
            imports.append(pkg)
        elif raw := match.group("import_pkg"):
            for chunk in raw.split(","):
                imports.append(chunk.strip().split(" as ")[0].strip())
    return imports


def test_no_llm_sdk_in_source():
    violations: list[tuple[Path, str]] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        for imp in _iter_imports(py_file.read_text(encoding="utf-8")):
            top = imp.split(".")[0]
            if top in FORBIDDEN_TOP_LEVEL or imp in FORBIDDEN_DOTTED:
                violations.append((py_file, imp))
    assert not violations, "LLM SDK imports are forbidden; found: " + ", ".join(
        f"{p}:{imp}" for p, imp in violations
    )


def test_forbidden_packages_not_in_pyproject():
    pyproject = (SRC_ROOT.parents[1] / "pyproject.toml").read_text()
    for pkg in FORBIDDEN_TOP_LEVEL | {"google-generativeai", "google-genai"}:
        assert pkg not in pyproject.lower(), f"{pkg} must not appear in pyproject.toml"
```

- [ ] **Step 2: Run — expect pass (source has no LLM imports yet)**

```bash
pytest tests/contract/test_no_llm_sdk.py -v
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/contract/test_no_llm_sdk.py
git commit -m "test(contract): enforce no LLM SDK imports (Hard Invariant #2)"
```

---

### Task 6: CI configuration

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `config.toml.example`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - name: Install
        run: pip install -e '.[dev]'
      - name: Lint
        run: ruff check src/ tests/
      - name: Format check
        run: ruff format --check src/ tests/
      - name: Test
        run: pytest --cov=src --cov-report=term-missing
```

- [ ] **Step 2: Write `config.toml.example`**

```toml
# Copy to ~/.social-research-probe/config.toml (or pass --data-dir).
# Secrets live in a separate ~/.social-research-probe/secrets.toml (chmod 0600).

[llm]
runner = "none"           # claude | gemini | codex | local | none
timeout_seconds = 60

[llm.claude]
model = "sonnet"
extra_flags = []

[llm.gemini]
model = "gemini-2.5-pro"
extra_flags = []

[llm.codex]
binary = "codex"
model = "gpt-4o"
extra_flags = []

[llm.local]
binary = "ollama"
model = "llama3.1:8b"
extra_flags = []

[scoring.weights]
# Overrides for spec §6 defaults (element-wise-max merged with purpose overrides).

[corroboration]
backend = "host"          # host | llm_cli | exa | brave | tavily | none
max_claims_per_item = 5
max_claims_per_session = 15

[platforms.youtube]
recency_days = 90
max_items = 20
cache_ttl_search_hours = 6
cache_ttl_channel_hours = 24
```

- [ ] **Step 3: Lint locally**

```bash
ruff check src/ tests/
ruff format --check src/ tests/
pytest
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml config.toml.example
git commit -m "chore(ci): add GitHub Actions workflow + config example"
```

---

**End of Phase P0.** You now have: installable package, `srp --help` works, SKILL.md + 10 reference stubs in place, CI green, Hard Invariant #2 enforced.

---

## Phase P1 — State + Commands + Config/Secrets

Goal: `srp` manages `topics.json`, `purposes.json`, `pending_suggestions.json` with atomic writes, schema validation, version-chain migration, and dedupe. All non-research commands work end-to-end. Secrets storage + `srp config` subcommand complete.

---

### Task 7: Config resolution (data-dir, config.toml)

**Files:**
- Create: `src/social_research_probe/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing test `tests/unit/test_config.py`**

```python
"""Data-dir resolution order and config.toml loading."""
from __future__ import annotations

from pathlib import Path

import pytest

from social_research_probe.config import Config, resolve_data_dir


def test_data_dir_flag_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path / "env"))
    result = resolve_data_dir(flag=str(tmp_path / "flag"), cwd=tmp_path)
    assert result == tmp_path / "flag"


def test_env_var_beats_cwd_and_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path / "env"))
    (tmp_path / ".skill-data").mkdir()
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == tmp_path / "env"


def test_cwd_skill_data_beats_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    local = tmp_path / ".skill-data"
    local.mkdir()
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == local


def test_fallback_to_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == tmp_path / "home" / ".social-research-probe"


def test_config_load_returns_defaults_when_missing(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_runner == "none"
    assert cfg.corroboration_backend == "host"
    assert cfg.platform_defaults("youtube")["max_items"] == 20


def test_config_load_reads_toml(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[llm]\nrunner = "claude"\ntimeout_seconds = 30\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_runner == "claude"
    assert cfg.llm_timeout_seconds == 30
```

- [ ] **Step 2: Run — expect import failure**

```bash
pytest tests/unit/test_config.py -v
```

- [ ] **Step 3: Write `src/social_research_probe/config.py`**

```python
"""Data-dir resolution + config.toml loading. Does NOT read secrets — see secrets.py."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "llm": {"runner": "none", "timeout_seconds": 60},
    "corroboration": {
        "backend": "host",
        "max_claims_per_item": 5,
        "max_claims_per_session": 15,
    },
    "platforms": {
        "youtube": {
            "recency_days": 90,
            "max_items": 20,
            "cache_ttl_search_hours": 6,
            "cache_ttl_channel_hours": 24,
        },
    },
    "scoring": {"weights": {}},
}


def resolve_data_dir(flag: str | None, cwd: Path | None = None) -> Path:
    """Resolve data dir in precedence: flag > env > cwd/.skill-data > ~/.social-research-probe."""
    if flag:
        return Path(flag).expanduser().resolve()
    if env := os.environ.get("SRP_DATA_DIR"):
        return Path(env).expanduser().resolve()
    cwd = cwd or Path.cwd()
    local = cwd / ".skill-data"
    if local.is_dir():
        return local.resolve()
    return (Path.home() / ".social-research-probe").resolve()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


@dataclass(frozen=True)
class Config:
    data_dir: Path
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, data_dir: Path) -> Config:
        data_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = data_dir / "config.toml"
        merged = dict(DEFAULT_CONFIG)
        if cfg_path.exists():
            with cfg_path.open("rb") as f:
                user = tomllib.load(f)
            merged = _deep_merge(merged, user)
        return cls(data_dir=data_dir, raw=merged)

    @property
    def llm_runner(self) -> str:
        return self.raw["llm"]["runner"]

    @property
    def llm_timeout_seconds(self) -> int:
        return int(self.raw["llm"]["timeout_seconds"])

    @property
    def corroboration_backend(self) -> str:
        return self.raw["corroboration"]["backend"]

    def platform_defaults(self, name: str) -> dict[str, Any]:
        return dict(self.raw["platforms"].get(name, {}))
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/config.py tests/unit/test_config.py
git commit -m "feat(config): data-dir resolution + config.toml loader"
```

---

### Task 8: State store (atomic JSON read/write + seeding)

**Files:**
- Create: `src/social_research_probe/state/__init__.py` (empty)
- Create: `src/social_research_probe/state/store.py`
- Create: `tests/unit/test_state_store.py`

- [ ] **Step 1: Write failing test `tests/unit/test_state_store.py`**

```python
"""Atomic writes, default seeding, POSIX os.replace semantics."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.state.store import atomic_write_json, read_json


def test_read_missing_file_seeds_defaults(tmp_path: Path):
    path = tmp_path / "topics.json"
    default = {"schema_version": 1, "topics": []}
    result = read_json(path, default_factory=lambda: default)
    assert result == default
    assert path.exists()
    assert json.loads(path.read_text()) == default


def test_read_existing_file_returns_content(tmp_path: Path):
    path = tmp_path / "topics.json"
    path.write_text(json.dumps({"schema_version": 1, "topics": ["a"]}))
    result = read_json(path, default_factory=lambda: {"x": 1})
    assert result["topics"] == ["a"]


def test_atomic_write_overwrites(tmp_path: Path):
    path = tmp_path / "topics.json"
    atomic_write_json(path, {"v": 1})
    atomic_write_json(path, {"v": 2})
    assert json.loads(path.read_text()) == {"v": 2}


def test_atomic_write_leaves_no_tmp_files(tmp_path: Path):
    path = tmp_path / "topics.json"
    atomic_write_json(path, {"v": 1})
    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert not tmp_files, f"temp files leaked: {tmp_files}"


def test_atomic_write_creates_parent_dir(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "topics.json"
    atomic_write_json(path, {"v": 1})
    assert path.exists()


def test_atomic_write_formatting(tmp_path: Path):
    path = tmp_path / "f.json"
    atomic_write_json(path, {"b": 2, "a": 1})
    content = path.read_text()
    assert content.endswith("\n")
    assert "  " in content  # indent=2
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/state/__init__.py` (empty)**

```python
```

- [ ] **Step 4: Write `src/social_research_probe/state/store.py`**

```python
"""Atomic JSON reader/writer. POSIX-atomic replace; fsync before rename."""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


def read_json(path: Path, default_factory: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Read JSON; if file missing, seed with default_factory() and persist."""
    if not path.exists():
        data = default_factory()
        atomic_write_json(path, data)
        return data
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: tmp -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
```

- [ ] **Step 5: Run — expect pass**

```bash
pytest tests/unit/test_state_store.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/social_research_probe/state/ tests/unit/test_state_store.py
git commit -m "feat(state): atomic JSON read/write with default seeding"
```

---

### Task 9: State schemas + validation

**Files:**
- Create: `src/social_research_probe/state/schemas.py`
- Create: `src/social_research_probe/state/validate.py`
- Create: `tests/unit/test_state_schemas.py`

- [ ] **Step 1: Write failing test `tests/unit/test_state_schemas.py`**

```python
"""jsonschema validation for topics.json, purposes.json, pending_suggestions.json."""
from __future__ import annotations

import pytest

from social_research_probe.errors import ValidationError
from social_research_probe.state.schemas import (
    PENDING_SUGGESTIONS_SCHEMA,
    PURPOSES_SCHEMA,
    TOPICS_SCHEMA,
    default_pending_suggestions,
    default_purposes,
    default_topics,
)
from social_research_probe.state.validate import validate


def test_topics_defaults_are_valid():
    validate(default_topics(), TOPICS_SCHEMA)


def test_purposes_defaults_are_valid():
    validate(default_purposes(), PURPOSES_SCHEMA)


def test_pending_defaults_are_valid():
    validate(default_pending_suggestions(), PENDING_SUGGESTIONS_SCHEMA)


def test_topics_rejects_missing_schema_version():
    with pytest.raises(ValidationError):
        validate({"topics": []}, TOPICS_SCHEMA)


def test_topics_rejects_non_string_topic():
    with pytest.raises(ValidationError):
        validate({"schema_version": 1, "topics": [42]}, TOPICS_SCHEMA)


def test_purposes_rejects_missing_method():
    bad = {"schema_version": 1, "purposes": {"trends": {"evidence_priorities": []}}}
    with pytest.raises(ValidationError):
        validate(bad, PURPOSES_SCHEMA)


def test_pending_rejects_duplicate_ids():
    # Schema allows dups; uniqueness is enforced at write-time in commands (Task 14).
    # This test locks in the schema shape: each entry must have id+value fields.
    bad = {"schema_version": 1, "pending_topic_suggestions": [{"id": 1}], "pending_purpose_suggestions": []}
    with pytest.raises(ValidationError):
        validate(bad, PENDING_SUGGESTIONS_SCHEMA)
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/state/schemas.py`**

```python
"""jsonschema definitions + default factories for every state file."""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1

TOPICS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["schema_version", "topics"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "topics": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}

PURPOSE_ENTRY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["method", "evidence_priorities"],
    "additionalProperties": False,
    "properties": {
        "method": {"type": "string", "minLength": 1},
        "evidence_priorities": {"type": "array", "items": {"type": "string"}},
        "scoring_overrides": {"type": "object"},
    },
}

PURPOSES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["schema_version", "purposes"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "purposes": {
            "type": "object",
            "additionalProperties": PURPOSE_ENTRY_SCHEMA,
        },
    },
}

PENDING_TOPIC_ENTRY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["id", "value", "reason", "duplicate_status", "matches"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "value": {"type": "string", "minLength": 1},
        "reason": {"type": "string"},
        "duplicate_status": {"enum": ["new", "near-duplicate", "duplicate"]},
        "matches": {"type": "array", "items": {"type": "string"}},
    },
}

PENDING_PURPOSE_ENTRY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["id", "name", "method", "evidence_priorities", "duplicate_status", "matches"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "name": {"type": "string", "minLength": 1},
        "method": {"type": "string", "minLength": 1},
        "evidence_priorities": {"type": "array", "items": {"type": "string"}},
        "duplicate_status": {"enum": ["new", "near-duplicate", "duplicate"]},
        "matches": {"type": "array", "items": {"type": "string"}},
    },
}

PENDING_SUGGESTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["schema_version", "pending_topic_suggestions", "pending_purpose_suggestions"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "pending_topic_suggestions": {"type": "array", "items": PENDING_TOPIC_ENTRY_SCHEMA},
        "pending_purpose_suggestions": {"type": "array", "items": PENDING_PURPOSE_ENTRY_SCHEMA},
    },
}


def default_topics() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "topics": []}


def default_purposes() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "purposes": {}}


def default_pending_suggestions() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "pending_topic_suggestions": [],
        "pending_purpose_suggestions": [],
    }
```

- [ ] **Step 4: Write `src/social_research_probe/state/validate.py`**

```python
"""Thin wrapper around jsonschema that raises SrpError.ValidationError on failure."""
from __future__ import annotations

from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from social_research_probe.errors import ValidationError


def validate(data: Any, schema: dict[str, Any]) -> None:
    """Strict validation; raises ValidationError listing all issues."""
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    messages = [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
    raise ValidationError("; ".join(messages))
```

- [ ] **Step 5: Run — expect pass**

```bash
pytest tests/unit/test_state_schemas.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/social_research_probe/state/schemas.py src/social_research_probe/state/validate.py tests/unit/test_state_schemas.py
git commit -m "feat(state): jsonschema definitions + validation wrapper"
```

---

### Task 10: Migration chain + backup

**Files:**
- Create: `src/social_research_probe/state/migrate.py`
- Create: `tests/unit/test_state_migrate.py`

- [ ] **Step 1: Write failing test `tests/unit/test_state_migrate.py`**

```python
"""Version-chain migrators. Idempotent. Backup before overwrite."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.errors import MigrationError
from social_research_probe.state.migrate import migrate_to_current, migrators_for
from social_research_probe.state.schemas import SCHEMA_VERSION


def test_current_version_is_noop(tmp_path: Path):
    path = tmp_path / "topics.json"
    data = {"schema_version": SCHEMA_VERSION, "topics": ["a"]}
    result = migrate_to_current(path, data, kind="topics")
    assert result == data


def test_missing_schema_version_treated_as_zero(tmp_path: Path):
    path = tmp_path / "topics.json"
    data = {"topics": ["a"]}  # no schema_version
    result = migrate_to_current(path, data, kind="topics")
    assert result["schema_version"] == SCHEMA_VERSION


def test_unknown_future_version_raises(tmp_path: Path):
    path = tmp_path / "topics.json"
    data = {"schema_version": 999, "topics": []}
    with pytest.raises(MigrationError):
        migrate_to_current(path, data, kind="topics")


def test_backup_written_before_migration(tmp_path: Path):
    path = tmp_path / "topics.json"
    path.write_text(json.dumps({"topics": ["legacy"]}))
    data = json.loads(path.read_text())
    migrate_to_current(path, data, kind="topics")
    backups = list((tmp_path / ".backups").glob("topics.v0.*.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text()) == {"topics": ["legacy"]}


def test_migrators_for_known_kinds():
    # Migrators registry covers all three state files.
    assert migrators_for("topics") is not None
    assert migrators_for("purposes") is not None
    assert migrators_for("pending_suggestions") is not None
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/state/migrate.py`**

```python
"""Ordered version-chain migrators. Pure functions; backup before overwrite."""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from social_research_probe.errors import MigrationError
from social_research_probe.state.schemas import SCHEMA_VERSION

# Each migrator takes (data) -> data at version+1.
Migrator = Callable[[dict[str, Any]], dict[str, Any]]


def _tag_version_1(data: dict[str, Any]) -> dict[str, Any]:
    """v0 -> v1: stamp schema_version=1 on bare legacy files."""
    out = dict(data)
    out["schema_version"] = 1
    return out


# kind -> ordered list of migrators, index i migrates v_i to v_{i+1}.
_MIGRATORS: dict[str, list[Migrator]] = {
    "topics": [_tag_version_1],
    "purposes": [_tag_version_1],
    "pending_suggestions": [_tag_version_1],
}


def migrators_for(kind: str) -> list[Migrator]:
    if kind not in _MIGRATORS:
        raise MigrationError(f"no migrators registered for kind={kind!r}")
    return _MIGRATORS[kind]


def _write_backup(path: Path, data: dict[str, Any], version: int) -> None:
    backup_dir = path.parent / ".backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    backup_path = backup_dir / f"{path.stem}.v{version}.{ts}.json"
    backup_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def migrate_to_current(path: Path, data: dict[str, Any], *, kind: str) -> dict[str, Any]:
    """Run forward migrators until data.schema_version == SCHEMA_VERSION."""
    current = int(data.get("schema_version", 0))
    target = SCHEMA_VERSION

    if current == target:
        return data
    if current > target:
        raise MigrationError(
            f"{path.name} has schema_version={current}, but this build supports {target}"
        )

    chain = migrators_for(kind)
    if current >= len(chain) + 1:  # no migrator covers this version
        raise MigrationError(f"{path.name} at v{current} has no migration path to v{target}")

    _write_backup(path, data, current)
    out = data
    for step_idx in range(current, target):
        migrator = chain[step_idx]
        out = migrator(out)
    return out
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_state_migrate.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/state/migrate.py tests/unit/test_state_migrate.py
git commit -m "feat(state): version-chain migrators with pre-migration backups"
```

---

### Task 11: Dedupe (rapidfuzz)

**Files:**
- Create: `src/social_research_probe/dedupe.py`
- Create: `tests/unit/test_dedupe.py`

- [ ] **Step 1: Write failing test `tests/unit/test_dedupe.py`**

```python
"""rapidfuzz-backed dedupe: exact -> duplicate, near -> near-duplicate, else -> new."""
from __future__ import annotations

from social_research_probe.dedupe import DuplicateStatus, classify


def test_exact_match_is_duplicate():
    result = classify("ai agents", existing=["ai agents", "robotics"])
    assert result.status is DuplicateStatus.DUPLICATE
    assert result.matches == ["ai agents"]


def test_case_and_whitespace_insensitive():
    result = classify("  AI Agents  ", existing=["ai agents"])
    assert result.status is DuplicateStatus.DUPLICATE


def test_near_match_is_near_duplicate():
    result = classify("ai agent", existing=["ai agents"])
    assert result.status is DuplicateStatus.NEAR_DUPLICATE
    assert "ai agents" in result.matches


def test_unrelated_is_new():
    result = classify("quantum computing", existing=["ai agents", "robotics"])
    assert result.status is DuplicateStatus.NEW
    assert result.matches == []


def test_empty_existing_is_new():
    result = classify("anything", existing=[])
    assert result.status is DuplicateStatus.NEW


def test_threshold_is_documented():
    # Locks in the default thresholds so they can be tuned via config later.
    from social_research_probe.dedupe import DUPLICATE_THRESHOLD, NEAR_DUPLICATE_THRESHOLD
    assert DUPLICATE_THRESHOLD == 95
    assert NEAR_DUPLICATE_THRESHOLD == 80
    assert NEAR_DUPLICATE_THRESHOLD < DUPLICATE_THRESHOLD
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/dedupe.py`**

```python
"""Duplicate detection using rapidfuzz token_set_ratio."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz, process

DUPLICATE_THRESHOLD = 95
NEAR_DUPLICATE_THRESHOLD = 80


class DuplicateStatus(str, Enum):
    NEW = "new"
    NEAR_DUPLICATE = "near-duplicate"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class DedupeResult:
    status: DuplicateStatus
    matches: list[str]


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def classify(candidate: str, existing: list[str]) -> DedupeResult:
    """Return DedupeResult comparing candidate to existing entries."""
    if not existing:
        return DedupeResult(DuplicateStatus.NEW, [])

    norm_candidate = _normalize(candidate)
    normalized = {_normalize(e): e for e in existing}

    scored = process.extract(
        norm_candidate,
        list(normalized.keys()),
        scorer=fuzz.token_set_ratio,
        limit=len(normalized),
    )

    dup = [normalized[name] for name, score, _ in scored if score >= DUPLICATE_THRESHOLD]
    if dup:
        return DedupeResult(DuplicateStatus.DUPLICATE, dup)

    near = [normalized[name] for name, score, _ in scored if score >= NEAR_DUPLICATE_THRESHOLD]
    if near:
        return DedupeResult(DuplicateStatus.NEAR_DUPLICATE, near)

    return DedupeResult(DuplicateStatus.NEW, [])
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_dedupe.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/dedupe.py tests/unit/test_dedupe.py
git commit -m "feat(dedupe): rapidfuzz token_set_ratio-based classifier"
```

---

### Task 12: DSL parser (recursive-descent)

**Files:**
- Create: `src/social_research_probe/commands/__init__.py` (empty)
- Create: `src/social_research_probe/commands/parse.py`
- Create: `tests/unit/test_parse.py`

- [ ] **Step 1: Write failing test `tests/unit/test_parse.py`**

```python
"""Deterministic DSL parser. Grammar locked in by tests."""
from __future__ import annotations

import pytest

from social_research_probe.commands.parse import (
    ParsedApplyPending,
    ParsedDiscardPending,
    ParsedRunResearch,
    ParsedUpdatePurposes,
    ParsedUpdateTopics,
    ParseError,
    parse,
)


def test_update_topics_add():
    result = parse('update-topics add:"ai agents"|"robotics"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "add"
    assert result.values == ["ai agents", "robotics"]


def test_update_topics_remove():
    result = parse('update-topics remove:"ai agents"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "remove"
    assert result.values == ["ai agents"]


def test_update_topics_rename():
    result = parse('update-topics rename:"old name"->"new name"')
    assert isinstance(result, ParsedUpdateTopics)
    assert result.op == "rename"
    assert result.rename_from == "old name"
    assert result.rename_to == "new name"


def test_update_purposes_add_with_method():
    result = parse('update-purposes add:"trends"="Track emergence across channels"')
    assert isinstance(result, ParsedUpdatePurposes)
    assert result.op == "add"
    assert result.name == "trends"
    assert result.method == "Track emergence across channels"


def test_apply_pending_all():
    result = parse("apply-pending-suggestions topics:all purposes:all")
    assert isinstance(result, ParsedApplyPending)
    assert result.topic_ids == "all"
    assert result.purpose_ids == "all"


def test_apply_pending_ids():
    result = parse("apply-pending-suggestions topics:1,3 purposes:2,4")
    assert isinstance(result, ParsedApplyPending)
    assert result.topic_ids == [1, 3]
    assert result.purpose_ids == [2, 4]


def test_discard_pending():
    result = parse("discard-pending-suggestions topics:2 purposes:all")
    assert isinstance(result, ParsedDiscardPending)
    assert result.topic_ids == [2]
    assert result.purpose_ids == "all"


def test_run_research_single_topic():
    result = parse('run-research platform:youtube "ai agents"->trends')
    assert isinstance(result, ParsedRunResearch)
    assert result.platform == "youtube"
    assert result.topics == [("ai agents", ["trends"])]


def test_run_research_combined_purposes():
    result = parse('run-research platform:youtube "ai agents"->trends+job-opportunities')
    assert isinstance(result, ParsedRunResearch)
    assert result.topics == [("ai agents", ["trends", "job-opportunities"])]


def test_run_research_multiple_topics():
    result = parse('run-research platform:youtube "ai agents"->trends;"robotics"->trends+arbitrage')
    assert isinstance(result, ParsedRunResearch)
    assert result.topics == [
        ("ai agents", ["trends"]),
        ("robotics", ["trends", "arbitrage"]),
    ]


def test_unquoted_topic_raises():
    with pytest.raises(ParseError):
        parse("update-topics add:ai agents")


def test_empty_raises():
    with pytest.raises(ParseError):
        parse("")


def test_unknown_command_raises():
    with pytest.raises(ParseError):
        parse('wobbulate "x"')
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/commands/__init__.py`** (empty file)

- [ ] **Step 4: Write `src/social_research_probe/commands/parse.py`**

```python
"""Recursive-descent parser for the srp command DSL. Never consults an LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

from social_research_probe.errors import SrpError


class ParseError(SrpError):
    exit_code = 2


# --- AST ---------------------------------------------------------------------

@dataclass(frozen=True)
class ParsedUpdateTopics:
    op: Literal["add", "remove", "rename"]
    values: list[str] = field(default_factory=list)
    rename_from: str | None = None
    rename_to: str | None = None


@dataclass(frozen=True)
class ParsedShowTopics:
    pass


@dataclass(frozen=True)
class ParsedUpdatePurposes:
    op: Literal["add", "remove", "rename"]
    name: str | None = None
    method: str | None = None
    values: list[str] = field(default_factory=list)
    rename_from: str | None = None
    rename_to: str | None = None


@dataclass(frozen=True)
class ParsedShowPurposes:
    pass


@dataclass(frozen=True)
class ParsedSuggestTopics:
    pass


@dataclass(frozen=True)
class ParsedSuggestPurposes:
    pass


@dataclass(frozen=True)
class ParsedShowPending:
    pass


@dataclass(frozen=True)
class ParsedApplyPending:
    topic_ids: Union[Literal["all"], list[int]]
    purpose_ids: Union[Literal["all"], list[int]]


@dataclass(frozen=True)
class ParsedDiscardPending:
    topic_ids: Union[Literal["all"], list[int]]
    purpose_ids: Union[Literal["all"], list[int]]


@dataclass(frozen=True)
class ParsedRunResearch:
    platform: str
    topics: list[tuple[str, list[str]]]  # [(topic, [purpose, ...]), ...]


Parsed = Union[
    ParsedUpdateTopics,
    ParsedShowTopics,
    ParsedUpdatePurposes,
    ParsedShowPurposes,
    ParsedSuggestTopics,
    ParsedSuggestPurposes,
    ParsedShowPending,
    ParsedApplyPending,
    ParsedDiscardPending,
    ParsedRunResearch,
]


# --- Lexer helpers -----------------------------------------------------------

def _take_quoted(src: str, pos: int) -> tuple[str, int]:
    if pos >= len(src) or src[pos] != '"':
        raise ParseError(f"expected '\"' at position {pos}")
    end = src.find('"', pos + 1)
    if end == -1:
        raise ParseError("unterminated quoted string")
    return src[pos + 1 : end], end + 1


def _parse_quoted_list(src: str) -> list[str]:
    # Parse "a"|"b"|"c"
    values: list[str] = []
    pos = 0
    while pos < len(src):
        val, pos = _take_quoted(src, pos)
        values.append(val)
        if pos < len(src):
            if src[pos] != "|":
                raise ParseError(f"expected '|' or end at position {pos} in {src!r}")
            pos += 1
    return values


def _parse_id_selector(src: str) -> Union[Literal["all"], list[int]]:
    if src == "all":
        return "all"
    try:
        return [int(x.strip()) for x in src.split(",") if x.strip()]
    except ValueError as exc:
        raise ParseError(f"invalid id selector: {src!r}") from exc


# --- Command dispatch --------------------------------------------------------

def parse(text: str) -> Parsed:
    text = text.strip()
    if not text:
        raise ParseError("empty command")

    head, _, tail = text.partition(" ")
    tail = tail.strip()

    dispatch = {
        "update-topics": _parse_update_topics,
        "show-topics": lambda _: ParsedShowTopics(),
        "update-purposes": _parse_update_purposes,
        "show-purposes": lambda _: ParsedShowPurposes(),
        "suggest-topics": lambda _: ParsedSuggestTopics(),
        "suggest-purposes": lambda _: ParsedSuggestPurposes(),
        "show-pending-suggestions": lambda _: ParsedShowPending(),
        "apply-pending-suggestions": _parse_apply_pending,
        "discard-pending-suggestions": _parse_discard_pending,
        "run-research": _parse_run_research,
    }
    if head not in dispatch:
        raise ParseError(f"unknown command: {head!r}")
    return dispatch[head](tail)


def _parse_update_topics(tail: str) -> ParsedUpdateTopics:
    if tail.startswith("add:"):
        return ParsedUpdateTopics(op="add", values=_parse_quoted_list(tail[4:]))
    if tail.startswith("remove:"):
        return ParsedUpdateTopics(op="remove", values=_parse_quoted_list(tail[7:]))
    if tail.startswith("rename:"):
        rest = tail[7:]
        old, pos = _take_quoted(rest, 0)
        if rest[pos : pos + 2] != "->":
            raise ParseError("expected '->' in rename")
        new, _ = _take_quoted(rest, pos + 2)
        return ParsedUpdateTopics(op="rename", rename_from=old, rename_to=new)
    raise ParseError(f"expected add:/remove:/rename:, got {tail!r}")


def _parse_update_purposes(tail: str) -> ParsedUpdatePurposes:
    if tail.startswith("add:"):
        rest = tail[4:]
        name, pos = _take_quoted(rest, 0)
        if rest[pos : pos + 2] != '="':
            raise ParseError("expected '=' followed by quoted method")
        method, _ = _take_quoted(rest, pos + 1)
        return ParsedUpdatePurposes(op="add", name=name, method=method)
    if tail.startswith("remove:"):
        return ParsedUpdatePurposes(op="remove", values=_parse_quoted_list(tail[7:]))
    if tail.startswith("rename:"):
        rest = tail[7:]
        old, pos = _take_quoted(rest, 0)
        if rest[pos : pos + 2] != "->":
            raise ParseError("expected '->' in rename")
        new, _ = _take_quoted(rest, pos + 2)
        return ParsedUpdatePurposes(op="rename", rename_from=old, rename_to=new)
    raise ParseError(f"expected add:/remove:/rename:, got {tail!r}")


def _parse_apply_pending(tail: str) -> ParsedApplyPending:
    topic_ids, purpose_ids = _parse_pending_selectors(tail)
    return ParsedApplyPending(topic_ids=topic_ids, purpose_ids=purpose_ids)


def _parse_discard_pending(tail: str) -> ParsedDiscardPending:
    topic_ids, purpose_ids = _parse_pending_selectors(tail)
    return ParsedDiscardPending(topic_ids=topic_ids, purpose_ids=purpose_ids)


def _parse_pending_selectors(tail: str) -> tuple[Union[Literal["all"], list[int]], Union[Literal["all"], list[int]]]:
    parts = dict(_kv_pair(chunk) for chunk in tail.split())
    if "topics" not in parts or "purposes" not in parts:
        raise ParseError("apply/discard requires topics:... and purposes:...")
    return _parse_id_selector(parts["topics"]), _parse_id_selector(parts["purposes"])


def _kv_pair(chunk: str) -> tuple[str, str]:
    key, _, val = chunk.partition(":")
    if not val:
        raise ParseError(f"expected key:value, got {chunk!r}")
    return key, val


def _parse_run_research(tail: str) -> ParsedRunResearch:
    if not tail.startswith("platform:"):
        raise ParseError("run-research must start with platform:NAME")
    rest = tail[len("platform:") :]
    platform_name, _, topic_section = rest.partition(" ")
    if not platform_name or not topic_section:
        raise ParseError("run-research expects 'platform:NAME <topic>->p1+p2;...'")

    topics: list[tuple[str, list[str]]] = []
    for entry in topic_section.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        topic, pos = _take_quoted(entry, 0)
        if entry[pos : pos + 2] != "->":
            raise ParseError(f"expected '->' after topic in {entry!r}")
        purposes = [p.strip() for p in entry[pos + 2 :].split("+") if p.strip()]
        if not purposes:
            raise ParseError(f"topic {topic!r} has no purposes")
        topics.append((topic, purposes))

    if not topics:
        raise ParseError("run-research needs at least one topic")
    return ParsedRunResearch(platform=platform_name, topics=topics)
```

- [ ] **Step 5: Run — expect pass**

```bash
pytest tests/unit/test_parse.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/social_research_probe/commands/__init__.py src/social_research_probe/commands/parse.py tests/unit/test_parse.py
git commit -m "feat(commands): recursive-descent DSL parser for all subcommands"
```

---

### Task 13: Topics commands (add/remove/rename/show)

**Files:**
- Create: `src/social_research_probe/commands/topics.py`
- Create: `tests/unit/test_topics.py`

- [ ] **Step 1: Write failing test `tests/unit/test_topics.py`**

```python
"""Topics CRUD with dedupe + atomic writes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.commands.topics import (
    add_topics,
    remove_topics,
    rename_topic,
    show_topics,
)
from social_research_probe.errors import DuplicateError


def _read(data_dir: Path) -> dict:
    return json.loads((data_dir / "topics.json").read_text())


def test_add_new_topics(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents", "robotics"], force=False)
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents", "robotics"]


def test_add_keeps_alphabetical_order(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["robotics"], force=False)
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents", "robotics"]


def test_add_exact_duplicate_exits_3(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    with pytest.raises(DuplicateError):
        add_topics(tmp_data_dir, ["ai agents"], force=False)


def test_add_near_duplicate_exits_3(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    with pytest.raises(DuplicateError):
        add_topics(tmp_data_dir, ["ai agent"], force=False)


def test_add_with_force_overrides(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    add_topics(tmp_data_dir, ["ai agent"], force=True)
    state = _read(tmp_data_dir)
    assert "ai agent" in state["topics"]
    assert "ai agents" in state["topics"]


def test_remove_existing(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents", "robotics"], force=False)
    remove_topics(tmp_data_dir, ["robotics"])
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents"]


def test_remove_missing_is_noop(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    remove_topics(tmp_data_dir, ["nonexistent"])
    state = _read(tmp_data_dir)
    assert state["topics"] == ["ai agents"]


def test_rename(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    rename_topic(tmp_data_dir, "ai agents", "autonomous agents")
    state = _read(tmp_data_dir)
    assert state["topics"] == ["autonomous agents"]


def test_show_returns_list(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    assert show_topics(tmp_data_dir) == ["ai agents"]
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/commands/topics.py`**

```python
"""Topics CRUD. Reads/writes topics.json through state.store, dedupes via dedupe.classify."""
from __future__ import annotations

from pathlib import Path

from social_research_probe.dedupe import DuplicateStatus, classify
from social_research_probe.errors import DuplicateError
from social_research_probe.state.migrate import migrate_to_current
from social_research_probe.state.schemas import TOPICS_SCHEMA, default_topics
from social_research_probe.state.store import atomic_write_json, read_json
from social_research_probe.state.validate import validate

_FILENAME = "topics.json"


def _load(data_dir: Path) -> dict:
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_topics)
    data = migrate_to_current(path, data, kind="topics")
    validate(data, TOPICS_SCHEMA)
    return data


def _save(data_dir: Path, data: dict) -> None:
    validate(data, TOPICS_SCHEMA)
    data["topics"] = sorted(set(data["topics"]))
    atomic_write_json(data_dir / _FILENAME, data)


def show_topics(data_dir: Path) -> list[str]:
    return list(_load(data_dir)["topics"])


def add_topics(data_dir: Path, values: list[str], *, force: bool) -> None:
    data = _load(data_dir)
    existing = list(data["topics"])
    to_add: list[str] = []
    conflicts: list[tuple[str, list[str]]] = []

    for value in values:
        result = classify(value, existing + to_add)
        if result.status is DuplicateStatus.NEW or force:
            to_add.append(value)
        elif result.status is DuplicateStatus.DUPLICATE:
            conflicts.append((value, result.matches))
        else:  # near-duplicate
            conflicts.append((value, result.matches))

    if conflicts and not force:
        descriptions = "; ".join(f"{v!r} ~ {m}" for v, m in conflicts)
        raise DuplicateError(f"duplicate/near-duplicate topics: {descriptions} (use --force to override)")

    data["topics"] = existing + to_add
    _save(data_dir, data)


def remove_topics(data_dir: Path, values: list[str]) -> None:
    data = _load(data_dir)
    remove_set = set(values)
    data["topics"] = [t for t in data["topics"] if t not in remove_set]
    _save(data_dir, data)


def rename_topic(data_dir: Path, old: str, new: str) -> None:
    data = _load(data_dir)
    topics = [new if t == old else t for t in data["topics"]]
    data["topics"] = topics
    _save(data_dir, data)
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_topics.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/commands/topics.py tests/unit/test_topics.py
git commit -m "feat(commands): topics CRUD with dedupe + atomic persistence"
```

---

### Task 14: Purposes commands (add/remove/rename/show) + registry

**Files:**
- Create: `src/social_research_probe/purposes/__init__.py` (empty)
- Create: `src/social_research_probe/purposes/registry.py`
- Create: `src/social_research_probe/commands/purposes.py`
- Create: `tests/unit/test_purposes.py`

- [ ] **Step 1: Write failing test `tests/unit/test_purposes.py`**

```python
"""Purposes CRUD: method string required on add; dedupe on name."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.commands.purposes import (
    add_purpose,
    remove_purposes,
    rename_purpose,
    show_purposes,
)
from social_research_probe.errors import DuplicateError, ValidationError


def _read(data_dir: Path) -> dict:
    return json.loads((data_dir / "purposes.json").read_text())


def test_add_new_purpose(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="Track emergence", force=False)
    state = _read(tmp_data_dir)
    assert "trends" in state["purposes"]
    assert state["purposes"]["trends"]["method"] == "Track emergence"
    assert state["purposes"]["trends"]["evidence_priorities"] == []


def test_add_duplicate_name_exits_3(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="Track", force=False)
    with pytest.raises(DuplicateError):
        add_purpose(tmp_data_dir, name="trends", method="Different", force=False)


def test_add_requires_nonempty_method(tmp_data_dir: Path):
    with pytest.raises(ValidationError):
        add_purpose(tmp_data_dir, name="trends", method="", force=False)


def test_remove(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    add_purpose(tmp_data_dir, name="career", method="y", force=False)
    remove_purposes(tmp_data_dir, ["trends"])
    state = _read(tmp_data_dir)
    assert list(state["purposes"].keys()) == ["career"]


def test_rename(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    rename_purpose(tmp_data_dir, "trends", "trend-analysis")
    state = _read(tmp_data_dir)
    assert "trends" not in state["purposes"]
    assert "trend-analysis" in state["purposes"]


def test_show(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    assert show_purposes(tmp_data_dir) == {"trends": {"method": "x", "evidence_priorities": [], "scoring_overrides": {}}}
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/purposes/__init__.py`** (empty file)

- [ ] **Step 4: Write `src/social_research_probe/purposes/registry.py`**

```python
"""Purpose lookup + persistence helpers (read/write purposes.json)."""
from __future__ import annotations

from pathlib import Path

from social_research_probe.state.migrate import migrate_to_current
from social_research_probe.state.schemas import PURPOSES_SCHEMA, default_purposes
from social_research_probe.state.store import atomic_write_json, read_json
from social_research_probe.state.validate import validate

_FILENAME = "purposes.json"


def load(data_dir: Path) -> dict:
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_purposes)
    data = migrate_to_current(path, data, kind="purposes")
    validate(data, PURPOSES_SCHEMA)
    return data


def save(data_dir: Path, data: dict) -> None:
    validate(data, PURPOSES_SCHEMA)
    atomic_write_json(data_dir / _FILENAME, data)


def get(data_dir: Path, name: str) -> dict:
    data = load(data_dir)
    if name not in data["purposes"]:
        raise KeyError(name)
    return dict(data["purposes"][name])
```

- [ ] **Step 5: Write `src/social_research_probe/commands/purposes.py`**

```python
"""Purposes CRUD."""
from __future__ import annotations

from pathlib import Path

from social_research_probe.dedupe import DuplicateStatus, classify
from social_research_probe.errors import DuplicateError, ValidationError
from social_research_probe.purposes import registry


def show_purposes(data_dir: Path) -> dict:
    data = registry.load(data_dir)
    out = {}
    for name, entry in data["purposes"].items():
        out[name] = {
            "method": entry["method"],
            "evidence_priorities": list(entry.get("evidence_priorities", [])),
            "scoring_overrides": dict(entry.get("scoring_overrides", {})),
        }
    return out


def add_purpose(data_dir: Path, *, name: str, method: str, force: bool) -> None:
    if not method.strip():
        raise ValidationError("purpose method cannot be empty")

    data = registry.load(data_dir)
    existing_names = list(data["purposes"].keys())

    result = classify(name, existing_names)
    if result.status is not DuplicateStatus.NEW and not force:
        raise DuplicateError(
            f"purpose {name!r} {result.status.value} with {result.matches} (use --force to override)"
        )

    data["purposes"][name] = {
        "method": method,
        "evidence_priorities": [],
        "scoring_overrides": {},
    }
    registry.save(data_dir, data)


def remove_purposes(data_dir: Path, names: list[str]) -> None:
    data = registry.load(data_dir)
    for n in names:
        data["purposes"].pop(n, None)
    registry.save(data_dir, data)


def rename_purpose(data_dir: Path, old: str, new: str) -> None:
    data = registry.load(data_dir)
    if old not in data["purposes"]:
        return
    data["purposes"][new] = data["purposes"].pop(old)
    registry.save(data_dir, data)
```

- [ ] **Step 6: Run — expect pass**

```bash
pytest tests/unit/test_purposes.py -v
```

- [ ] **Step 7: Commit**

```bash
git add src/social_research_probe/purposes/ src/social_research_probe/commands/purposes.py tests/unit/test_purposes.py
git commit -m "feat(commands): purposes CRUD + registry module"
```

---

### Task 15: Purpose merge (MergedPurpose computation)

**Files:**
- Create: `src/social_research_probe/purposes/merge.py`
- Create: `tests/unit/test_purpose_merge.py`

- [ ] **Step 1: Write failing test `tests/unit/test_purpose_merge.py`**

```python
"""Purpose merge: union evidence_priorities (preserve order), concat methods,
element-wise-max scoring_overrides (strictest trust wins)."""
from __future__ import annotations

from social_research_probe.purposes.merge import MergedPurpose, merge_purposes


def test_single_purpose_passthrough():
    purposes = {
        "trends": {
            "method": "Track emergence",
            "evidence_priorities": ["view velocity", "recency"],
            "scoring_overrides": {"trust": 0.5},
        }
    }
    merged = merge_purposes(purposes, ["trends"])
    assert merged.method == "Track emergence"
    assert merged.evidence_priorities == ["view velocity", "recency"]
    assert merged.scoring_overrides == {"trust": 0.5}


def test_two_purposes_union_evidence_preserve_order():
    purposes = {
        "trends": {"method": "A", "evidence_priorities": ["a", "b"], "scoring_overrides": {}},
        "career": {"method": "B", "evidence_priorities": ["b", "c"], "scoring_overrides": {}},
    }
    merged = merge_purposes(purposes, ["trends", "career"])
    assert merged.evidence_priorities == ["a", "b", "c"]


def test_method_concat_dedup():
    purposes = {
        "trends": {"method": "A", "evidence_priorities": [], "scoring_overrides": {}},
        "career": {"method": "B", "evidence_priorities": [], "scoring_overrides": {}},
        "dup": {"method": "A", "evidence_priorities": [], "scoring_overrides": {}},
    }
    merged = merge_purposes(purposes, ["trends", "career", "dup"])
    assert merged.method == "A\nB"  # dup "A" omitted


def test_scoring_overrides_element_wise_max():
    purposes = {
        "lax": {"method": "x", "evidence_priorities": [], "scoring_overrides": {"trust": 0.3, "trend": 0.2}},
        "strict": {"method": "y", "evidence_priorities": [], "scoring_overrides": {"trust": 0.7}},
    }
    merged = merge_purposes(purposes, ["lax", "strict"])
    assert merged.scoring_overrides == {"trust": 0.7, "trend": 0.2}


def test_unknown_purpose_raises():
    import pytest
    from social_research_probe.errors import ValidationError

    with pytest.raises(ValidationError):
        merge_purposes({}, ["nonexistent"])


def test_merged_is_frozen_dataclass():
    purposes = {"p": {"method": "x", "evidence_priorities": [], "scoring_overrides": {}}}
    merged = merge_purposes(purposes, ["p"])
    assert isinstance(merged, MergedPurpose)
    import pytest
    with pytest.raises(Exception):  # frozen
        merged.method = "changed"  # type: ignore[misc]
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/purposes/merge.py`**

```python
"""Purpose composition. Deterministic, pure."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from social_research_probe.errors import ValidationError


@dataclass(frozen=True)
class MergedPurpose:
    names: tuple[str, ...]
    method: str
    evidence_priorities: tuple[str, ...]
    scoring_overrides: dict[str, float] = field(default_factory=dict)


def merge_purposes(purposes: dict[str, dict[str, Any]], selected: list[str]) -> MergedPurpose:
    missing = [n for n in selected if n not in purposes]
    if missing:
        raise ValidationError(f"unknown purpose(s): {missing}")

    method_lines: list[str] = []
    seen_methods: set[str] = set()
    evidence: list[str] = []
    seen_evidence: set[str] = set()
    overrides: dict[str, float] = {}

    for name in selected:
        entry = purposes[name]
        method = entry["method"]
        if method not in seen_methods:
            method_lines.append(method)
            seen_methods.add(method)
        for pri in entry.get("evidence_priorities", []):
            if pri not in seen_evidence:
                evidence.append(pri)
                seen_evidence.add(pri)
        for key, val in entry.get("scoring_overrides", {}).items():
            if key not in overrides or val > overrides[key]:
                overrides[key] = float(val)

    return MergedPurpose(
        names=tuple(selected),
        method="\n".join(method_lines),
        evidence_priorities=tuple(evidence),
        scoring_overrides=overrides,
    )
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_purpose_merge.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/purposes/merge.py tests/unit/test_purpose_merge.py
git commit -m "feat(purposes): MergedPurpose composition (union + element-wise-max)"
```

---

### Task 16: Rule-based suggestions + staging

**Files:**
- Create: `src/social_research_probe/commands/suggestions.py`
- Create: `tests/unit/test_suggestions.py`

Suggestions in P1 are **rule-based only** — gaps in the topic × purpose matrix. Host-LLM enhancement lands in P4.

- [ ] **Step 1: Write failing test `tests/unit/test_suggestions.py`**

```python
"""Rule-based topic/purpose suggestions + pending staging."""
from __future__ import annotations

import json
from pathlib import Path

from social_research_probe.commands.purposes import add_purpose
from social_research_probe.commands.suggestions import (
    apply_pending,
    discard_pending,
    show_pending,
    stage_suggestions,
    suggest_purposes,
    suggest_topics,
)
from social_research_probe.commands.topics import add_topics


def _pending(data_dir: Path) -> dict:
    return json.loads((data_dir / "pending_suggestions.json").read_text())


def test_suggest_topics_emits_gap_candidates(tmp_data_dir: Path):
    # Seed some topics; suggest-topics produces draft list tagged "gap".
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    drafts = suggest_topics(tmp_data_dir, count=3)
    assert len(drafts) <= 3
    for d in drafts:
        assert "value" in d
        assert "reason" in d
        assert d["reason"] == "gap"


def test_suggest_purposes_emits_gap_candidates(tmp_data_dir: Path):
    add_purpose(tmp_data_dir, name="trends", method="x", force=False)
    drafts = suggest_purposes(tmp_data_dir, count=3)
    assert len(drafts) <= 3
    for d in drafts:
        assert "name" in d
        assert "method" in d


def test_stage_suggestions_assigns_ids_and_dedupe(tmp_data_dir: Path):
    add_topics(tmp_data_dir, ["ai agents"], force=False)
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[
            {"value": "on-device LLMs", "reason": "gap"},
            {"value": "ai agent", "reason": "gap"},  # near-dup of "ai agents"
        ],
        purpose_candidates=[],
    )
    state = _pending(tmp_data_dir)
    topics = state["pending_topic_suggestions"]
    assert len(topics) == 2
    assert topics[0]["id"] == 1
    assert topics[1]["id"] == 2
    new_entry = next(t for t in topics if t["value"] == "on-device LLMs")
    near_entry = next(t for t in topics if t["value"] == "ai agent")
    assert new_entry["duplicate_status"] == "new"
    assert near_entry["duplicate_status"] == "near-duplicate"
    assert "ai agents" in near_entry["matches"]


def test_show_pending(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "a", "reason": "gap"}],
        purpose_candidates=[],
    )
    result = show_pending(tmp_data_dir)
    assert len(result["pending_topic_suggestions"]) == 1
    assert len(result["pending_purpose_suggestions"]) == 0


def test_apply_pending_all(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "x", "reason": "gap"}],
        purpose_candidates=[{"name": "p", "method": "m", "evidence_priorities": []}],
    )
    apply_pending(tmp_data_dir, topic_ids="all", purpose_ids="all")
    topics = json.loads((tmp_data_dir / "topics.json").read_text())["topics"]
    purposes = json.loads((tmp_data_dir / "purposes.json").read_text())["purposes"]
    assert "x" in topics
    assert "p" in purposes
    assert _pending(tmp_data_dir)["pending_topic_suggestions"] == []
    assert _pending(tmp_data_dir)["pending_purpose_suggestions"] == []


def test_apply_pending_by_ids(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "x", "reason": "gap"}, {"value": "y", "reason": "gap"}],
        purpose_candidates=[],
    )
    apply_pending(tmp_data_dir, topic_ids=[1], purpose_ids="all")
    topics = json.loads((tmp_data_dir / "topics.json").read_text())["topics"]
    assert topics == ["x"]
    remaining = _pending(tmp_data_dir)["pending_topic_suggestions"]
    assert len(remaining) == 1
    assert remaining[0]["value"] == "y"


def test_discard_pending_removes_without_applying(tmp_data_dir: Path):
    stage_suggestions(
        tmp_data_dir,
        topic_candidates=[{"value": "x", "reason": "gap"}],
        purpose_candidates=[],
    )
    discard_pending(tmp_data_dir, topic_ids="all", purpose_ids="all")
    topics = json.loads((tmp_data_dir / "topics.json").read_text())["topics"]
    assert topics == []
    assert _pending(tmp_data_dir)["pending_topic_suggestions"] == []
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/commands/suggestions.py`**

```python
"""Rule-based suggestions + staging. Host-LLM enhancement lands in P4."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Union

from social_research_probe.commands.purposes import add_purpose
from social_research_probe.commands.topics import add_topics
from social_research_probe.dedupe import DuplicateStatus, classify
from social_research_probe.errors import ValidationError
from social_research_probe.purposes import registry as purposes_registry
from social_research_probe.state.migrate import migrate_to_current
from social_research_probe.state.schemas import (
    PENDING_SUGGESTIONS_SCHEMA,
    default_pending_suggestions,
)
from social_research_probe.state.store import atomic_write_json, read_json
from social_research_probe.state.validate import validate

_FILENAME = "pending_suggestions.json"

# Rule-based seed pool. Real P4 enhancement via host LLM adds creative topics;
# for P1, we emit placeholder "gap" candidates from these well-known domains.
_TOPIC_SEED_POOL = [
    "on-device LLMs",
    "robotics foundation models",
    "vector databases",
    "AI-generated video",
    "tool-using agents",
    "model context protocol",
    "open weight models",
    "multimodal agents",
]

_PURPOSE_SEED_POOL = [
    ("saturation-analysis", "Detect when a topic has peaked; measure repetition across channels."),
    ("audience-fit", "Match content style to viewer demographics; gauge retention signals."),
    ("arbitrage", "Find pricing/attention spreads between platforms or niches."),
    ("job-opportunities", "Identify hiring signals and skill demand from creator content."),
]


def _load_pending(data_dir: Path) -> dict:
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_pending_suggestions)
    data = migrate_to_current(path, data, kind="pending_suggestions")
    validate(data, PENDING_SUGGESTIONS_SCHEMA)
    return data


def _save_pending(data_dir: Path, data: dict) -> None:
    validate(data, PENDING_SUGGESTIONS_SCHEMA)
    atomic_write_json(data_dir / _FILENAME, data)


def _next_id(entries: list[dict]) -> int:
    return max((e["id"] for e in entries), default=0) + 1


def suggest_topics(data_dir: Path, count: int = 5) -> list[dict[str, Any]]:
    from social_research_probe.commands.topics import show_topics

    existing = show_topics(data_dir)
    drafts: list[dict[str, Any]] = []
    for candidate in _TOPIC_SEED_POOL:
        if len(drafts) >= count:
            break
        if classify(candidate, existing).status is DuplicateStatus.NEW:
            drafts.append({"value": candidate, "reason": "gap"})
    return drafts


def suggest_purposes(data_dir: Path, count: int = 5) -> list[dict[str, Any]]:
    from social_research_probe.commands.purposes import show_purposes

    existing = list(show_purposes(data_dir).keys())
    drafts: list[dict[str, Any]] = []
    for name, method in _PURPOSE_SEED_POOL:
        if len(drafts) >= count:
            break
        if classify(name, existing).status is DuplicateStatus.NEW:
            drafts.append({"name": name, "method": method, "evidence_priorities": []})
    return drafts


def stage_suggestions(
    data_dir: Path,
    *,
    topic_candidates: list[dict[str, Any]],
    purpose_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    from social_research_probe.commands.topics import show_topics
    from social_research_probe.commands.purposes import show_purposes

    pending = _load_pending(data_dir)
    existing_topics = show_topics(data_dir)
    existing_purposes = list(show_purposes(data_dir).keys())

    for cand in topic_candidates:
        if "value" not in cand:
            raise ValidationError(f"topic candidate missing 'value': {cand}")
        result = classify(cand["value"], existing_topics)
        entry = {
            "id": _next_id(pending["pending_topic_suggestions"]),
            "value": cand["value"],
            "reason": cand.get("reason", "gap"),
            "duplicate_status": result.status.value,
            "matches": list(result.matches),
        }
        pending["pending_topic_suggestions"].append(entry)

    for cand in purpose_candidates:
        if "name" not in cand or "method" not in cand:
            raise ValidationError(f"purpose candidate missing name/method: {cand}")
        result = classify(cand["name"], existing_purposes)
        entry = {
            "id": _next_id(pending["pending_purpose_suggestions"]),
            "name": cand["name"],
            "method": cand["method"],
            "evidence_priorities": list(cand.get("evidence_priorities", [])),
            "duplicate_status": result.status.value,
            "matches": list(result.matches),
        }
        pending["pending_purpose_suggestions"].append(entry)

    _save_pending(data_dir, pending)
    return pending


def show_pending(data_dir: Path) -> dict:
    return _load_pending(data_dir)


IdSelector = Union[Literal["all"], list[int]]


def _select(entries: list[dict], selector: IdSelector) -> tuple[list[dict], list[dict]]:
    if selector == "all":
        return entries, []
    ids = set(selector)
    chosen = [e for e in entries if e["id"] in ids]
    remaining = [e for e in entries if e["id"] not in ids]
    return chosen, remaining


def apply_pending(data_dir: Path, *, topic_ids: IdSelector, purpose_ids: IdSelector) -> None:
    pending = _load_pending(data_dir)

    topic_chosen, topic_rest = _select(pending["pending_topic_suggestions"], topic_ids)
    purpose_chosen, purpose_rest = _select(pending["pending_purpose_suggestions"], purpose_ids)

    for entry in topic_chosen:
        try:
            add_topics(data_dir, [entry["value"]], force=False)
        except Exception:
            # Requeue on failure; dedupe re-check is authoritative.
            topic_rest.append(entry)

    for entry in purpose_chosen:
        try:
            add_purpose(data_dir, name=entry["name"], method=entry["method"], force=False)
        except Exception:
            purpose_rest.append(entry)

    pending["pending_topic_suggestions"] = topic_rest
    pending["pending_purpose_suggestions"] = purpose_rest
    _save_pending(data_dir, pending)


def discard_pending(data_dir: Path, *, topic_ids: IdSelector, purpose_ids: IdSelector) -> None:
    pending = _load_pending(data_dir)
    _, topic_rest = _select(pending["pending_topic_suggestions"], topic_ids)
    _, purpose_rest = _select(pending["pending_purpose_suggestions"], purpose_ids)
    pending["pending_topic_suggestions"] = topic_rest
    pending["pending_purpose_suggestions"] = purpose_rest
    _save_pending(data_dir, pending)
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_suggestions.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/commands/suggestions.py tests/unit/test_suggestions.py
git commit -m "feat(commands): rule-based suggestions + pending staging (apply/discard)"
```

---

### Task 17: `srp config` subcommand (show/path/set/set-secret/unset-secret/check-secrets)

**Files:**
- Create: `src/social_research_probe/commands/config.py`
- Create: `tests/unit/test_config_cmd.py`

Secrets live in a separate file (`~/.social-research-probe/secrets.toml`) with `0600` permissions. Values are resolved in order: `SRP_<NAME>` env var → secrets.toml → unset.

- [ ] **Step 1: Write failing test `tests/unit/test_config_cmd.py`**

```python
"""srp config subcommand: set/get/check for non-secret and secret values."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from social_research_probe.commands.config import (
    SECRET_FILENAME,
    check_secrets,
    mask_secret,
    read_secret,
    show_config,
    unset_secret,
    write_config_value,
    write_secret,
)


def test_write_and_read_secret(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "AIzaTESTVALUE123")
    assert read_secret(tmp_data_dir, "youtube_api_key") == "AIzaTESTVALUE123"


def test_secret_file_has_0600_perms(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "x")
    path = tmp_data_dir / SECRET_FILENAME
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"


def test_env_var_overrides_file(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    write_secret(tmp_data_dir, "youtube_api_key", "from-file")
    monkeypatch.setenv("SRP_YOUTUBE_API_KEY", "from-env")
    assert read_secret(tmp_data_dir, "youtube_api_key") == "from-env"


def test_unset_secret_removes(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "x")
    unset_secret(tmp_data_dir, "youtube_api_key")
    assert read_secret(tmp_data_dir, "youtube_api_key") is None


def test_mask_secret_short():
    assert mask_secret("abc") == "***"


def test_mask_secret_long():
    assert mask_secret("abcdef1234567890") == "abcd...7890"


def test_show_config_masks_secrets(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "AIzaTESTLONGVALUE")
    out = show_config(tmp_data_dir)
    assert "AIzaTESTLONGVALUE" not in out
    assert "..." in out  # masked
    assert "youtube_api_key" in out


def test_check_secrets_structure(tmp_data_dir: Path):
    result = check_secrets(
        tmp_data_dir,
        needed_for="run-research",
        platform="youtube",
        corroboration=None,
    )
    assert set(result.keys()) == {"required", "optional", "present", "missing"}
    assert "youtube_api_key" in result["required"]
    assert "youtube_api_key" in result["missing"]


def test_check_secrets_detects_present(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "x")
    result = check_secrets(
        tmp_data_dir,
        needed_for="run-research",
        platform="youtube",
        corroboration=None,
    )
    assert "youtube_api_key" in result["present"]
    assert result["missing"] == []


def test_write_config_value(tmp_data_dir: Path):
    write_config_value(tmp_data_dir, "llm.runner", "claude")
    content = (tmp_data_dir / "config.toml").read_text()
    assert 'runner = "claude"' in content
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/commands/config.py`**

```python
"""srp config subcommand: non-secret config + secrets file management."""
from __future__ import annotations

import json
import os
import stat
import tomllib
from pathlib import Path
from typing import Any

from social_research_probe.config import Config

SECRET_FILENAME = "secrets.toml"
CONFIG_FILENAME = "config.toml"

# Map of (needed_for, platform, corroboration) -> required/optional secret names.
_PLATFORM_SECRETS: dict[str, list[str]] = {
    "youtube": ["youtube_api_key"],
}

_CORROBORATION_SECRETS: dict[str, list[str]] = {
    "exa": ["exa_api_key"],
    "brave": ["brave_api_key"],
    "tavily": ["tavily_api_key"],
}


def _env_key(name: str) -> str:
    return f"SRP_{name.upper()}"


def _read_secrets_file(data_dir: Path) -> dict[str, str]:
    path = data_dir / SECRET_FILENAME
    if not path.exists():
        return {}
    _check_perms(path)
    with path.open("rb") as f:
        parsed = tomllib.load(f)
    secrets = parsed.get("secrets", {})
    return {str(k): str(v) for k, v in secrets.items()}


def _check_perms(path: Path) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        import sys
        print(
            f"warning: {path} has permissions {oct(mode)}; should be 0600",
            file=sys.stderr,
        )


def _write_secrets_file(data_dir: Path, secrets: dict[str, str]) -> None:
    path = data_dir / SECRET_FILENAME
    data_dir.mkdir(parents=True, exist_ok=True)
    prev_umask = os.umask(0o077)
    try:
        lines = ["[secrets]"]
        for key, val in sorted(secrets.items()):
            escaped = val.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
    finally:
        os.umask(prev_umask)


def read_secret(data_dir: Path, name: str) -> str | None:
    env_val = os.environ.get(_env_key(name))
    if env_val:
        return env_val
    secrets = _read_secrets_file(data_dir)
    return secrets.get(name)


def write_secret(data_dir: Path, name: str, value: str) -> None:
    secrets = _read_secrets_file(data_dir)
    secrets[name] = value
    _write_secrets_file(data_dir, secrets)


def unset_secret(data_dir: Path, name: str) -> None:
    secrets = _read_secrets_file(data_dir)
    secrets.pop(name, None)
    _write_secrets_file(data_dir, secrets)


def mask_secret(value: str) -> str:
    if len(value) < 8:
        return "*" * min(len(value), 3) or "***"
    return f"{value[:4]}...{value[-4:]}"


def show_config(data_dir: Path) -> str:
    cfg = Config.load(data_dir)
    secrets = _read_secrets_file(data_dir)
    lines = [
        f"data_dir: {data_dir}",
        f"config_file: {data_dir / CONFIG_FILENAME}",
        f"secrets_file: {data_dir / SECRET_FILENAME}",
        "",
        "[config]",
        json.dumps(cfg.raw, indent=2),
        "",
        "[secrets]",
    ]
    for name, val in sorted(secrets.items()):
        env = os.environ.get(_env_key(name))
        if env:
            lines.append(f"  {name}: {mask_secret(env)}  (from env)")
        else:
            lines.append(f"  {name}: {mask_secret(val)}  (from file)")
    return "\n".join(lines)


def write_config_value(data_dir: Path, dotted_key: str, value: str) -> None:
    """Shallow config.toml writer: only supports dotted keys 1 level deep (e.g. llm.runner).

    Sufficient for P1 scope; richer nested writes land when actually needed.
    """
    parts = dotted_key.split(".")
    if len(parts) != 2:
        raise ValueError(f"config key must be section.key, got {dotted_key!r}")
    section, key = parts

    path = data_dir / CONFIG_FILENAME
    existing: dict[str, dict[str, Any]] = {}
    if path.exists():
        with path.open("rb") as f:
            existing = tomllib.load(f)

    existing.setdefault(section, {})[key] = value

    lines: list[str] = []
    for sec, entries in existing.items():
        lines.append(f"[{sec}]")
        for k, v in entries.items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, bool):
                lines.append(f"{k} = {'true' if v else 'false'}")
            else:
                lines.append(f"{k} = {v}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def check_secrets(
    data_dir: Path,
    *,
    needed_for: str | None,
    platform: str | None,
    corroboration: str | None,
) -> dict[str, list[str]]:
    required: list[str] = []
    optional: list[str] = []

    if needed_for == "run-research" and platform:
        required.extend(_PLATFORM_SECRETS.get(platform, []))
    if corroboration:
        required.extend(_CORROBORATION_SECRETS.get(corroboration, []))

    # Always list all platform/corroboration secrets not required as optional.
    all_known = {s for names in _PLATFORM_SECRETS.values() for s in names} | {
        s for names in _CORROBORATION_SECRETS.values() for s in names
    }
    optional = sorted(all_known - set(required))

    present = [name for name in (required + optional) if read_secret(data_dir, name) is not None]
    missing = [name for name in required if read_secret(data_dir, name) is None]

    return {
        "required": sorted(set(required)),
        "optional": optional,
        "present": sorted(set(present)),
        "missing": sorted(set(missing)),
    }
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/unit/test_config_cmd.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/commands/config.py tests/unit/test_config_cmd.py
git commit -m "feat(commands): srp config subcommand (secrets + config.toml + check)"
```

---

### Task 18: Wire all P1 subcommands into the CLI

**Files:**
- Modify: `src/social_research_probe/cli.py`
- Create: `tests/integration/test_state_cli.py`

- [ ] **Step 1: Write failing integration test `tests/integration/test_state_cli.py`**

```python
"""End-to-end CLI dispatch for state commands."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(data_dir: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **__import__("os").environ,
        "SRP_DATA_DIR": str(data_dir),
    }
    return subprocess.run(
        [sys.executable, "-m", "social_research_probe.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        input=stdin,
    )


def test_show_topics_empty(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir()
    result = _run(data_dir, "show-topics")
    assert result.returncode == 0
    assert "(no topics)" in result.stdout or result.stdout.strip() == ""


def test_add_then_show(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir()
    add = _run(data_dir, "update-topics", "--add", '"ai agents"|"robotics"')
    assert add.returncode == 0, add.stderr
    show = _run(data_dir, "show-topics", "--output", "json")
    assert show.returncode == 0
    payload = json.loads(show.stdout)
    assert sorted(payload["topics"]) == ["ai agents", "robotics"]


def test_duplicate_add_exits_3(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir()
    _run(data_dir, "update-topics", "--add", '"ai agents"')
    result = _run(data_dir, "update-topics", "--add", '"ai agents"')
    assert result.returncode == 3
    assert "duplicate" in result.stderr.lower() or "near-duplicate" in result.stderr.lower()


def test_config_check_secrets_json(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir()
    result = _run(
        data_dir,
        "config", "check-secrets",
        "--needed-for", "run-research",
        "--platform", "youtube",
        "--output", "json",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "youtube_api_key" in payload["missing"]


def test_config_set_secret_from_stdin(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir()
    result = _run(
        data_dir,
        "config", "set-secret", "youtube_api_key", "--from-stdin",
        stdin="AIzaSECRETVALUE12345",
    )
    assert result.returncode == 0
    check = _run(
        data_dir,
        "config", "check-secrets",
        "--needed-for", "run-research",
        "--platform", "youtube",
        "--output", "json",
    )
    payload = json.loads(check.stdout)
    assert "youtube_api_key" in payload["present"]


def test_suggest_and_apply(tmp_path: Path):
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir()
    suggest = _run(data_dir, "suggest-topics", "--count", "2", "--output", "json")
    assert suggest.returncode == 0
    # The CLI auto-stages when not in skill-mode emit-only path.
    show_pending = _run(data_dir, "show-pending", "--output", "json")
    pending = json.loads(show_pending.stdout)
    assert len(pending["pending_topic_suggestions"]) >= 1
    apply = _run(data_dir, "apply-pending", "--topics", "all")
    assert apply.returncode == 0
    topics = _run(data_dir, "show-topics", "--output", "json")
    assert json.loads(topics.stdout)["topics"]
```

- [ ] **Step 2: Run — expect failure (subcommands not registered)**

- [ ] **Step 3: Rewrite `src/social_research_probe/cli.py`** (full version replacing the stub)

```python
"""CLI entry point. All P1 subcommands wired up."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from social_research_probe import commands
from social_research_probe.commands import config as config_cmd
from social_research_probe.commands import purposes as purposes_cmd
from social_research_probe.commands import suggestions as suggestions_cmd
from social_research_probe.commands import topics as topics_cmd
from social_research_probe.commands.parse import _parse_quoted_list, _take_quoted
from social_research_probe.config import resolve_data_dir
from social_research_probe.errors import SrpError, ValidationError


def _global_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="srp", description="Evidence-first social-media research.")
    parser.add_argument("--mode", choices=["skill", "cli"], default="cli")
    parser.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    ut = sub.add_parser("update-topics")
    group = ut.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    ut.add_argument("--force", action="store_true")

    sub.add_parser("show-topics")

    up = sub.add_parser("update-purposes")
    group = up.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    up.add_argument("--force", action="store_true")

    sub.add_parser("show-purposes")

    st = sub.add_parser("suggest-topics")
    st.add_argument("--count", type=int, default=5)

    sp = sub.add_parser("suggest-purposes")
    sp.add_argument("--count", type=int, default=5)

    sub.add_parser("show-pending")

    ap = sub.add_parser("apply-pending")
    ap.add_argument("--topics", default="")
    ap.add_argument("--purposes", default="")

    dp = sub.add_parser("discard-pending")
    dp.add_argument("--topics", default="")
    dp.add_argument("--purposes", default="")

    ss = sub.add_parser("stage-suggestions")
    ss.add_argument("--from-stdin", action="store_true")

    cfg = sub.add_parser("config")
    cfg_sub = cfg.add_subparsers(dest="config_cmd", metavar="ACTION")
    cfg_sub.add_parser("show")
    cfg_sub.add_parser("path")
    set_p = cfg_sub.add_parser("set")
    set_p.add_argument("key")
    set_p.add_argument("value")
    sec_p = cfg_sub.add_parser("set-secret")
    sec_p.add_argument("name")
    sec_p.add_argument("--from-stdin", action="store_true")
    unset_p = cfg_sub.add_parser("unset-secret")
    unset_p.add_argument("name")
    check_p = cfg_sub.add_parser("check-secrets")
    check_p.add_argument("--needed-for", default=None)
    check_p.add_argument("--platform", default=None)
    check_p.add_argument("--corroboration", default=None)

    return parser


def _emit(data: object, fmt: str) -> None:
    if fmt == "json":
        json.dump(data, sys.stdout)
        sys.stdout.write("\n")
    elif fmt == "markdown":
        sys.stdout.write(_to_markdown(data) + "\n")
    else:
        sys.stdout.write(_to_text(data) + "\n")


def _to_text(data: object) -> str:
    if isinstance(data, dict) and "topics" in data:
        return "\n".join(data["topics"]) if data["topics"] else "(no topics)"
    if isinstance(data, dict) and "purposes" in data:
        if not data["purposes"]:
            return "(no purposes)"
        return "\n".join(f"{k}: {v['method']}" for k, v in data["purposes"].items())
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2)


def _to_markdown(data: object) -> str:
    return "```\n" + _to_text(data) + "\n```"


def _dispatch(args: argparse.Namespace) -> int:
    data_dir = resolve_data_dir(args.data_dir)

    if args.command == "update-topics":
        if args.add:
            values = _parse_quoted_list(args.add)
            topics_cmd.add_topics(data_dir, values, force=args.force)
        elif args.remove:
            values = _parse_quoted_list(args.remove)
            topics_cmd.remove_topics(data_dir, values)
        elif args.rename:
            old, pos = _take_quoted(args.rename, 0)
            if args.rename[pos : pos + 2] != "->":
                raise ValidationError("rename expects old->new")
            new, _ = _take_quoted(args.rename, pos + 2)
            topics_cmd.rename_topic(data_dir, old, new)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "show-topics":
        topics = topics_cmd.show_topics(data_dir)
        _emit({"topics": topics}, args.output)
        return 0

    if args.command == "update-purposes":
        if args.add:
            name, pos = _take_quoted(args.add, 0)
            if args.add[pos : pos + 1] != "=":
                raise ValidationError('add expects "name"="method"')
            method, _ = _take_quoted(args.add, pos + 1)
            purposes_cmd.add_purpose(data_dir, name=name, method=method, force=args.force)
        elif args.remove:
            purposes_cmd.remove_purposes(data_dir, _parse_quoted_list(args.remove))
        elif args.rename:
            old, pos = _take_quoted(args.rename, 0)
            if args.rename[pos : pos + 2] != "->":
                raise ValidationError("rename expects old->new")
            new, _ = _take_quoted(args.rename, pos + 2)
            purposes_cmd.rename_purpose(data_dir, old, new)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "show-purposes":
        _emit({"purposes": purposes_cmd.show_purposes(data_dir)}, args.output)
        return 0

    if args.command == "suggest-topics":
        drafts = suggestions_cmd.suggest_topics(data_dir, count=args.count)
        suggestions_cmd.stage_suggestions(data_dir, topic_candidates=drafts, purpose_candidates=[])
        _emit({"staged_topic_suggestions": drafts}, args.output)
        return 0

    if args.command == "suggest-purposes":
        drafts = suggestions_cmd.suggest_purposes(data_dir, count=args.count)
        suggestions_cmd.stage_suggestions(data_dir, topic_candidates=[], purpose_candidates=drafts)
        _emit({"staged_purpose_suggestions": drafts}, args.output)
        return 0

    if args.command == "show-pending":
        _emit(suggestions_cmd.show_pending(data_dir), args.output)
        return 0

    if args.command == "apply-pending":
        topic_sel = _id_selector(args.topics)
        purpose_sel = _id_selector(args.purposes)
        suggestions_cmd.apply_pending(data_dir, topic_ids=topic_sel, purpose_ids=purpose_sel)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "discard-pending":
        topic_sel = _id_selector(args.topics)
        purpose_sel = _id_selector(args.purposes)
        suggestions_cmd.discard_pending(data_dir, topic_ids=topic_sel, purpose_ids=purpose_sel)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "stage-suggestions":
        if not args.from_stdin:
            raise ValidationError("stage-suggestions requires --from-stdin")
        payload = json.loads(sys.stdin.read())
        suggestions_cmd.stage_suggestions(
            data_dir,
            topic_candidates=payload.get("topic_candidates", []),
            purpose_candidates=payload.get("purpose_candidates", []),
        )
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "config":
        return _dispatch_config(args, data_dir)

    return 2


def _id_selector(raw: str):
    if not raw:
        return []
    if raw == "all":
        return "all"
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise ValidationError(f"invalid id selector: {raw!r}") from exc


def _dispatch_config(args: argparse.Namespace, data_dir: Path) -> int:
    if args.config_cmd == "show":
        print(config_cmd.show_config(data_dir))
        return 0
    if args.config_cmd == "path":
        print(f"config: {data_dir / 'config.toml'}")
        print(f"secrets: {data_dir / 'secrets.toml'}")
        return 0
    if args.config_cmd == "set":
        config_cmd.write_config_value(data_dir, args.key, args.value)
        return 0
    if args.config_cmd == "set-secret":
        if args.from_stdin:
            value = sys.stdin.read().rstrip("\n")
        else:
            import getpass
            value = getpass.getpass(f"{args.name}: ")
        if not value:
            raise ValidationError("empty secret value")
        config_cmd.write_secret(data_dir, args.name, value)
        return 0
    if args.config_cmd == "unset-secret":
        config_cmd.unset_secret(data_dir, args.name)
        return 0
    if args.config_cmd == "check-secrets":
        result = config_cmd.check_secrets(
            data_dir,
            needed_for=args.needed_for,
            platform=args.platform,
            corroboration=args.corroboration,
        )
        _emit(result, args.output)
        return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = _global_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return _dispatch(args)
    except SrpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/integration/test_state_cli.py -v
pytest  # run everything
```

Expected: all tests pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/cli.py tests/integration/test_state_cli.py
git commit -m "feat(cli): wire all P1 subcommands + integration tests"
```

---

**End of Phase P1.** You now have: full state management (topics, purposes, pending suggestions) with atomic writes, migration, dedupe; rule-based suggestion generation; `srp config` + secrets with 0600 perms; end-to-end CLI integration tests green.

---

## Phase P2 — YouTube Adapter + Pipeline Shell + Skill-mode Output

Goal: `srp run-research --mode skill --platform youtube '"ai agents"->trends'` emits a valid `SkillPacket` JSON to stdout. The YouTube adapter is structured but its live network calls are exercised through a `FakeYouTubeAdapter` in tests. Real YouTube calls go through `fetch.py` but are only smoke-tested with an env key locally.

Note on stats/viz: per P2 scope in spec §14, sections 8–9 are stubbed with deterministic placeholder summaries. Real statistics + matplotlib land in P3.

---

### Task 19: Platform adapter base (dataclasses + ABC)

**Files:**
- Create: `src/social_research_probe/platforms/__init__.py` (empty)
- Create: `src/social_research_probe/platforms/base.py`
- Create: `tests/unit/test_platforms_base.py`

- [ ] **Step 1: Write failing test `tests/unit/test_platforms_base.py`**

```python
"""Platform adapter dataclasses + ABC contract."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)


def test_fetch_limits_defaults():
    limits = FetchLimits()
    assert limits.max_items == 20
    assert limits.recency_days == 90


def test_fetch_limits_is_frozen():
    limits = FetchLimits()
    with pytest.raises(Exception):
        limits.max_items = 5  # type: ignore[misc]


def test_raw_item_required_fields():
    item = RawItem(
        id="v1",
        url="https://example/v1",
        title="T",
        author_id="c1",
        author_name="Channel",
        published_at=datetime.now(timezone.utc),
        metrics={"views": 100},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    assert item.id == "v1"


def test_signal_set_allows_none_metrics():
    sig = SignalSet(
        views=None, likes=None, comments=None,
        upload_date=None,
        view_velocity=None, engagement_ratio=None,
        comment_velocity=None, cross_channel_repetition=None,
        raw={},
    )
    assert sig.views is None


def test_trust_hints_defaults_allow_nones():
    hints = TrustHints(
        account_age_days=None,
        verified=None,
        subscriber_count=None,
        upload_cadence_days=None,
        citation_markers=[],
    )
    assert hints.citation_markers == []


def test_adapter_is_abstract():
    with pytest.raises(TypeError):
        PlatformAdapter()  # type: ignore[abstract]
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/platforms/__init__.py`** (empty)

- [ ] **Step 4: Write `src/social_research_probe/platforms/base.py`**

```python
"""Platform adapter contract. All per-platform logic lives in subpackages."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar


@dataclass(frozen=True)
class FetchLimits:
    max_items: int = 20
    recency_days: int | None = 90


@dataclass(frozen=True)
class RawItem:
    id: str
    url: str
    title: str
    author_id: str
    author_name: str
    published_at: datetime
    metrics: dict[str, Any]
    text_excerpt: str | None
    thumbnail: str | None
    extras: dict[str, Any]


@dataclass(frozen=True)
class SignalSet:
    views: int | None
    likes: int | None
    comments: int | None
    upload_date: datetime | None
    view_velocity: float | None
    engagement_ratio: float | None
    comment_velocity: float | None
    cross_channel_repetition: float | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrustHints:
    account_age_days: int | None
    verified: bool | None
    subscriber_count: int | None
    upload_cadence_days: float | None
    citation_markers: list[str]


class PlatformAdapter(ABC):
    name: ClassVar[str]
    default_limits: ClassVar[FetchLimits]

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]: ...

    @abstractmethod
    def enrich(self, items: list[RawItem]) -> list[RawItem]: ...

    @abstractmethod
    def to_signals(self, items: list[RawItem]) -> list[SignalSet]: ...

    @abstractmethod
    def trust_hints(self, item: RawItem) -> TrustHints: ...

    @abstractmethod
    def url_normalize(self, url: str) -> str: ...

    def fetch_text_for_claim_extraction(self, item: RawItem) -> str | None:
        return None
```

- [ ] **Step 5: Run — expect pass**

```bash
pytest tests/unit/test_platforms_base.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/social_research_probe/platforms/__init__.py src/social_research_probe/platforms/base.py tests/unit/test_platforms_base.py
git commit -m "feat(platforms): adapter dataclasses + PlatformAdapter ABC"
```

---

### Task 20: Platform registry (@register + get_adapter)

**Files:**
- Create: `src/social_research_probe/platforms/registry.py`
- Create: `tests/unit/test_platforms_registry.py`

- [ ] **Step 1: Write failing test `tests/unit/test_platforms_registry.py`**

```python
"""Platform registry: @register, get_adapter, unknown platform raises."""
from __future__ import annotations

from typing import Any

import pytest

from social_research_probe.errors import ValidationError
from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import get_adapter, list_adapters, register


def test_register_and_get():
    @register
    class ToyAdapter(PlatformAdapter):
        name = "toy-registry-test"
        default_limits = FetchLimits()

        def __init__(self, config: dict[str, Any]) -> None:
            self.config = config

        def health_check(self) -> bool: return True
        def search(self, topic: str, limits: FetchLimits) -> list[RawItem]: return []
        def enrich(self, items: list[RawItem]) -> list[RawItem]: return items
        def to_signals(self, items: list[RawItem]) -> list[SignalSet]: return []
        def trust_hints(self, item: RawItem) -> TrustHints:
            return TrustHints(None, None, None, None, [])
        def url_normalize(self, url: str) -> str: return url

    adapter = get_adapter("toy-registry-test", {"k": "v"})
    assert isinstance(adapter, ToyAdapter)
    assert adapter.config == {"k": "v"}
    assert "toy-registry-test" in list_adapters()


def test_unknown_platform_raises():
    with pytest.raises(ValidationError) as excinfo:
        get_adapter("nonexistent", {})
    assert "nonexistent" in str(excinfo.value)
```

- [ ] **Step 2: Run — expect import failure**

- [ ] **Step 3: Write `src/social_research_probe/platforms/registry.py`**

```python
"""Module-level registry for platform adapters."""
from __future__ import annotations

from typing import Any

from social_research_probe.errors import ValidationError
from social_research_probe.platforms.base import PlatformAdapter

_REGISTRY: dict[str, type[PlatformAdapter]] = {}


def register(cls: type[PlatformAdapter]) -> type[PlatformAdapter]:
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_adapter(name: str, config: dict[str, Any]) -> PlatformAdapter:
    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown platform: {name!r} (registered: {known})")
    return _REGISTRY[name](config)


def list_adapters() -> list[str]:
    return sorted(_REGISTRY.keys())
```

- [ ] **Step 4: Run — expect pass**

- [ ] **Step 5: Commit**

```bash
git add src/social_research_probe/platforms/registry.py tests/unit/test_platforms_registry.py
git commit -m "feat(platforms): module-level registry with @register decorator"
```

---

### Task 21: FakeYouTubeAdapter test fixture

**Files:**
- Create: `tests/fixtures/__init__.py` (empty)
- Create: `tests/fixtures/fake_youtube.py`

This adapter is used by all P2 + P3 pipeline tests so they stay offline.

- [ ] **Step 1: Write `tests/fixtures/__init__.py`** (empty)

- [ ] **Step 2: Write `tests/fixtures/fake_youtube.py`**

```python
"""Deterministic YouTube-shaped adapter for tests. Registered on import."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import register


def _fixture_items(topic: str, n: int = 5) -> list[RawItem]:
    now = datetime.now(timezone.utc)
    items = []
    for i in range(n):
        items.append(
            RawItem(
                id=f"fake-{topic}-{i}",
                url=f"https://youtube.com/watch?v=fake{i}",
                title=f"{topic} — episode {i}",
                author_id=f"channel-{i % 3}",
                author_name=f"Channel {i % 3}",
                published_at=now - timedelta(days=i * 3),
                metrics={"views": 10_000 * (i + 1), "likes": 500 * (i + 1), "comments": 50 * (i + 1)},
                text_excerpt=f"A video about {topic}. Content {i}.",
                thumbnail=f"https://img/{i}.jpg",
                extras={"channel_subscribers": 50_000 + i * 1000},
            )
        )
    return items


@register
class FakeYouTubeAdapter(PlatformAdapter):
    name: ClassVar[str] = "youtube"
    default_limits: ClassVar[FetchLimits] = FetchLimits()

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def health_check(self) -> bool:
        return True

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        return _fixture_items(topic, n=min(5, limits.max_items))

    def enrich(self, items: list[RawItem]) -> list[RawItem]:
        return items

    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:
        now = datetime.now(timezone.utc)
        signals = []
        for item in items:
            age_days = max(1, (now - item.published_at).days)
            views = item.metrics.get("views", 0)
            likes = item.metrics.get("likes", 0)
            comments = item.metrics.get("comments", 0)
            signals.append(
                SignalSet(
                    views=views,
                    likes=likes,
                    comments=comments,
                    upload_date=item.published_at,
                    view_velocity=views / age_days,
                    engagement_ratio=(likes + comments) / max(1, views),
                    comment_velocity=comments / age_days,
                    cross_channel_repetition=0.0,  # filled by batch step
                    raw={},
                )
            )
        return signals

    def trust_hints(self, item: RawItem) -> TrustHints:
        return TrustHints(
            account_age_days=1200,
            verified=True,
            subscriber_count=int(item.extras.get("channel_subscribers", 0)),
            upload_cadence_days=7.0,
            citation_markers=[],
        )

    def url_normalize(self, url: str) -> str:
        return url.split("&")[0]

    def fetch_text_for_claim_extraction(self, item: RawItem) -> str | None:
        return item.text_excerpt
```

Note: this fixture registers as `name="youtube"`, pre-empting the real YouTube adapter during tests. That is intentional — tests import this fixture; production imports `social_research_probe.platforms.youtube` which will replace the registration at import time. Tests that exercise the real adapter (when added) must explicitly import it after clearing the fixture.

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/__init__.py tests/fixtures/fake_youtube.py
git commit -m "test(fixtures): FakeYouTubeAdapter for offline pipeline tests"
```

---

### Task 22: YouTube adapter skeleton (structure only; live calls stubbed)

**Files:**
- Create: `src/social_research_probe/platforms/youtube/__init__.py`
- Create: `src/social_research_probe/platforms/youtube/adapter.py`
- Create: `src/social_research_probe/platforms/youtube/fetch.py`
- Create: `src/social_research_probe/platforms/youtube/extract.py`
- Create: `src/social_research_probe/platforms/youtube/trust_hints.py`
- Create: `tests/unit/test_youtube_adapter_shape.py`

The real YouTube adapter is structured in P2 but its `search()` calls are exercised only via the fake adapter. Live smoke tests go in P7.

- [ ] **Step 1: Write failing test `tests/unit/test_youtube_adapter_shape.py`**

```python
"""YouTube adapter must satisfy PlatformAdapter ABC + raise AdapterError when
API key is missing."""
from __future__ import annotations

import pytest

from social_research_probe.errors import AdapterError


def test_adapter_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    from social_research_probe.platforms.youtube.adapter import YouTubeAdapter

    adapter = YouTubeAdapter({"data_dir": None})
    with pytest.raises(AdapterError):
        adapter.health_check()


def test_url_normalize_strips_extra_params():
    from social_research_probe.platforms.youtube.adapter import YouTubeAdapter

    adapter = YouTubeAdapter({"data_dir": None})
    url = "https://www.youtube.com/watch?v=abc123&t=30s&ab_channel=X"
    assert "v=abc123" in adapter.url_normalize(url)
    assert "ab_channel" not in adapter.url_normalize(url)
```

- [ ] **Step 2: Write `src/social_research_probe/platforms/youtube/__init__.py`**

```python
"""Importing this subpackage registers the real YouTubeAdapter."""
from social_research_probe.platforms.youtube.adapter import YouTubeAdapter  # noqa: F401
```

- [ ] **Step 3: Write `src/social_research_probe/platforms/youtube/fetch.py`**

```python
"""google-api-python-client wrappers. Real calls; tests don't import this."""
from __future__ import annotations

from typing import Any

from social_research_probe.errors import AdapterError


def build_client(api_key: str):  # pragma: no cover — live-only
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def search_videos(client: Any, *, topic: str, max_items: int, published_after: str | None) -> list[dict]:  # pragma: no cover
    try:
        resp = client.search().list(
            q=topic, part="snippet", type="video", maxResults=min(50, max_items),
            publishedAfter=published_after,
            order="viewCount",
        ).execute()
    except Exception as exc:
        raise AdapterError(f"youtube search failed: {exc}") from exc
    return resp.get("items", [])


def hydrate_videos(client: Any, *, video_ids: list[str]) -> list[dict]:  # pragma: no cover
    try:
        resp = client.videos().list(
            id=",".join(video_ids), part="snippet,statistics,contentDetails",
        ).execute()
    except Exception as exc:
        raise AdapterError(f"youtube videos.list failed: {exc}") from exc
    return resp.get("items", [])


def hydrate_channels(client: Any, *, channel_ids: list[str]) -> list[dict]:  # pragma: no cover
    try:
        resp = client.channels().list(
            id=",".join(channel_ids), part="snippet,statistics,brandingSettings",
        ).execute()
    except Exception as exc:
        raise AdapterError(f"youtube channels.list failed: {exc}") from exc
    return resp.get("items", [])
```

- [ ] **Step 4: Write `src/social_research_probe/platforms/youtube/extract.py`**

```python
"""yt-dlp-based transcript extraction. Lazy — only invoked by claim extraction (P6)."""
from __future__ import annotations


def fetch_transcript(url: str) -> str | None:  # pragma: no cover — network
    try:
        import yt_dlp
    except ImportError:
        return None
    opts = {"quiet": True, "skip_download": True, "writesubtitles": True, "subtitleslangs": ["en"]}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    subs = info.get("subtitles") or info.get("automatic_captions") or {}
    if "en" not in subs:
        return None
    return "\n".join(sub.get("data", "") for sub in subs["en"] if isinstance(sub, dict))
```

- [ ] **Step 5: Write `src/social_research_probe/platforms/youtube/trust_hints.py`**

```python
"""Channel-level trust signals: age, verified, subs, citation markers."""
from __future__ import annotations

import re
from datetime import datetime, timezone

_URL_RE = re.compile(r"https?://\S+")


def account_age_days(created_iso: str | None) -> int | None:
    if not created_iso:
        return None
    created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - created).days


def citation_markers(description: str | None) -> list[str]:
    if not description:
        return []
    return _URL_RE.findall(description)
```

- [ ] **Step 6: Write `src/social_research_probe/platforms/youtube/adapter.py`**

```python
"""Real YouTubeAdapter. In tests, `tests/fixtures/fake_youtube.py` pre-empts
this registration. In production, this module is imported and replaces the
fixture's registration."""
from __future__ import annotations

import os
from typing import Any, ClassVar

from social_research_probe.errors import AdapterError
from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import register


@register
class YouTubeAdapter(PlatformAdapter):
    name: ClassVar[str] = "youtube"
    default_limits: ClassVar[FetchLimits] = FetchLimits(max_items=20, recency_days=90)

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _api_key(self) -> str:
        key = os.environ.get("SRP_YOUTUBE_API_KEY")
        if key:
            return key
        data_dir = self.config.get("data_dir")
        if data_dir is not None:
            from social_research_probe.commands.config import read_secret
            val = read_secret(data_dir, "youtube_api_key")
            if val:
                return val
        raise AdapterError(
            "youtube_api_key missing — run `srp config set-secret youtube_api_key` in a terminal"
        )

    def health_check(self) -> bool:
        # Force key resolution so missing-key fails fast.
        self._api_key()
        return True

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:  # pragma: no cover — live
        from social_research_probe.platforms.youtube import fetch
        client = fetch.build_client(self._api_key())
        items = fetch.search_videos(client, topic=topic, max_items=limits.max_items, published_after=None)
        # Translation to RawItem happens in enrich() once videos.list is hydrated.
        return self._stub_items_from_search(items)

    def _stub_items_from_search(self, raw: list[dict]) -> list[RawItem]:  # pragma: no cover
        raise NotImplementedError("populated in P7 live smoke test; tests use FakeYouTubeAdapter")

    def enrich(self, items: list[RawItem]) -> list[RawItem]:  # pragma: no cover
        return items

    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:  # pragma: no cover
        return []

    def trust_hints(self, item: RawItem) -> TrustHints:  # pragma: no cover
        return TrustHints(None, None, None, None, [])

    def url_normalize(self, url: str) -> str:
        # Strip all query params except v=
        from urllib.parse import parse_qs, urlparse, urlunparse
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        keep = {"v": qs["v"]} if "v" in qs else {}
        query = "&".join(f"{k}={v[0]}" for k, v in keep.items())
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))
```

- [ ] **Step 7: Run — expect pass**

```bash
pytest tests/unit/test_youtube_adapter_shape.py -v
```

- [ ] **Step 8: Commit**

```bash
git add src/social_research_probe/platforms/youtube/ tests/unit/test_youtube_adapter_shape.py
git commit -m "feat(platforms/youtube): adapter skeleton with API-key resolution"
```

---

## Phase P2b — Source Classification & Scoring

### Task 23: Source classification (`validation/source.py`)

**Files:**
- Create: `src/social_research_probe/validation/__init__.py`
- Create: `src/social_research_probe/validation/source.py`
- Test:   `tests/unit/test_source.py`

- [ ] **Step 1: Failing test**

```python
# tests/unit/test_source.py
from datetime import datetime, timezone
from social_research_probe.platforms.base import RawItem, TrustHints
from social_research_probe.validation.source import SourceClass, classify

def _item(url="https://youtube.com/watch?v=x", extras=None):
    return RawItem(
        id="x", url=url, title="t",
        author_id="c1", author_name="c1",
        published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        metrics={}, text_excerpt=None, thumbnail=None,
        extras=extras or {},
    )

def test_primary_when_verified_and_old_channel():
    hints = TrustHints(account_age_days=3000, verified=True,
                       subscriber_count=500_000, upload_cadence_days=3.0,
                       citation_markers=["https://arxiv.org/abs/2401.0001"])
    assert classify(_item(), hints) is SourceClass.PRIMARY

def test_commentary_when_no_citations_and_young():
    hints = TrustHints(account_age_days=30, verified=False,
                       subscriber_count=50, upload_cadence_days=0.5,
                       citation_markers=[])
    assert classify(_item(), hints) is SourceClass.COMMENTARY

def test_secondary_default():
    hints = TrustHints(account_age_days=800, verified=False,
                       subscriber_count=20_000, upload_cadence_days=7.0,
                       citation_markers=["https://example.com/post"])
    assert classify(_item(), hints) is SourceClass.SECONDARY
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/unit/test_source.py -v
```

- [ ] **Step 3: Implement**

```python
# src/social_research_probe/validation/source.py
from __future__ import annotations
from enum import Enum
from social_research_probe.platforms.base import RawItem, TrustHints

_PRIMARY_DOMAINS = ("arxiv.org", "nature.com", "ieee.org", "acm.org",
                    ".gov", ".edu", "who.int", "nih.gov")

class SourceClass(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    COMMENTARY = "commentary"
    UNKNOWN = "unknown"

def _has_primary_citation(markers: list[str]) -> bool:
    return any(any(d in m.lower() for d in _PRIMARY_DOMAINS) for m in markers)

def classify(item: RawItem, hints: TrustHints) -> SourceClass:
    markers = hints.citation_markers or []
    age = hints.account_age_days or 0
    subs = hints.subscriber_count or 0
    verified = bool(hints.verified)

    if verified and age >= 365 and (_has_primary_citation(markers) or subs >= 100_000):
        return SourceClass.PRIMARY
    if not markers and age < 180 and subs < 5_000:
        return SourceClass.COMMENTARY
    if markers or subs >= 1_000:
        return SourceClass.SECONDARY
    return SourceClass.UNKNOWN
```

- [ ] **Step 4: Run — expect pass**; **Commit**

```bash
git add src/social_research_probe/validation/ tests/unit/test_source.py
git commit -m "feat(validation): source classification by trust hints and citations"
```

---

### Task 24: Scoring formulas (`scoring/`)

**Files:**
- Create: `src/social_research_probe/scoring/__init__.py`
- Create: `src/social_research_probe/scoring/trust.py`
- Create: `src/social_research_probe/scoring/trend.py`
- Create: `src/social_research_probe/scoring/opportunity.py`
- Create: `src/social_research_probe/scoring/combine.py`
- Test:   `tests/unit/test_scoring.py`
- Test:   `tests/unit/test_scoring_properties.py`

- [ ] **Step 1: Failing tests**

```python
# tests/unit/test_scoring.py
import math
from social_research_probe.scoring.trust import trust_score
from social_research_probe.scoring.trend import trend_score, recency_decay
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.combine import overall_score

def test_trust_bounds_and_formula():
    s = trust_score(source_class=1.0, channel_credibility=1.0,
                    citation_traceability=1.0, ai_slop_penalty=0.0,
                    corroboration_score=1.0)
    assert math.isclose(s, 1.0, abs_tol=1e-9)

def test_trend_recency_decay_monotonic():
    assert recency_decay(0) > recency_decay(30) > recency_decay(365)

def test_opportunity_bounds():
    s = opportunity_score(market_gap=0.0, monetization_proxy=0.0,
                          feasibility=0.0, novelty=0.0)
    assert s == 0.0

def test_overall_weights_sum_to_one():
    s = overall_score(trust=1.0, trend=1.0, opportunity=1.0)
    assert math.isclose(s, 1.0, abs_tol=1e-9)
```

```python
# tests/unit/test_scoring_properties.py
from hypothesis import given, strategies as st
from social_research_probe.scoring.combine import overall_score

unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

@given(trust_lo=unit, trust_hi=unit, trend=unit, opp=unit)
def test_trust_dominates_trend(trust_lo, trust_hi, trend, opp):
    lo = overall_score(trust=min(trust_lo, trust_hi), trend=trend, opportunity=opp)
    hi = overall_score(trust=max(trust_lo, trust_hi), trend=trend, opportunity=opp)
    assert hi >= lo
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/unit/test_scoring.py tests/unit/test_scoring_properties.py -v
```

- [ ] **Step 3: Implement**

```python
# src/social_research_probe/scoring/trust.py
def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))

def trust_score(*, source_class: float, channel_credibility: float,
                citation_traceability: float, ai_slop_penalty: float,
                corroboration_score: float) -> float:
    return _clip(
        0.35 * source_class
        + 0.25 * channel_credibility
        + 0.15 * citation_traceability
        + 0.15 * (1.0 - ai_slop_penalty)
        + 0.10 * corroboration_score
    )
```

```python
# src/social_research_probe/scoring/trend.py
import math

def _clip(x: float) -> float: return max(0.0, min(1.0, x))

def recency_decay(age_days: float) -> float:
    return math.exp(-max(0.0, age_days) / 30.0)

def trend_score(*, z_view_velocity: float, z_engagement_ratio: float,
                z_cross_channel_repetition: float, age_days: float) -> float:
    def norm_z(z: float) -> float: return _clip(0.5 + z / 6.0)
    return _clip(
        0.40 * norm_z(z_view_velocity)
        + 0.20 * norm_z(z_engagement_ratio)
        + 0.20 * norm_z(z_cross_channel_repetition)
        + 0.20 * recency_decay(age_days)
    )
```

```python
# src/social_research_probe/scoring/opportunity.py
def _clip(x: float) -> float: return max(0.0, min(1.0, x))

def opportunity_score(*, market_gap: float, monetization_proxy: float,
                      feasibility: float, novelty: float) -> float:
    return _clip(
        0.40 * market_gap
        + 0.30 * monetization_proxy
        + 0.20 * feasibility
        + 0.10 * novelty
    )
```

```python
# src/social_research_probe/scoring/combine.py
def _clip(x: float) -> float: return max(0.0, min(1.0, x))

def overall_score(*, trust: float, trend: float, opportunity: float) -> float:
    return _clip(0.45 * trust + 0.30 * trend + 0.25 * opportunity)
```

- [ ] **Step 4: Run — expect pass**; **Commit**

```bash
git add src/social_research_probe/scoring/ tests/unit/test_scoring.py tests/unit/test_scoring_properties.py
git commit -m "feat(scoring): trust/trend/opportunity/overall formulas with monotonicity test"
```

---

## Phase P2c — Skill-Mode Packet & Formatter

### Task 25: Host-LLM passthrough (`llm/host.py`)

**Files:**
- Create: `src/social_research_probe/llm/__init__.py`
- Create: `src/social_research_probe/llm/host.py`
- Test:   `tests/unit/test_llm_host.py`

- [ ] **Step 1: Failing test**

```python
# tests/unit/test_llm_host.py
import json, subprocess, sys, textwrap

def test_emit_packet_writes_json_and_exits_zero(tmp_path):
    script = tmp_path / "emit.py"
    script.write_text(textwrap.dedent("""
        from social_research_probe.llm.host import emit_packet
        emit_packet({"topic":"ai"}, kind="synthesis")
    """))
    p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert p.returncode == 0
    out = json.loads(p.stdout)
    assert out == {"skill_mode": True, "kind": "synthesis", "packet": {"topic":"ai"}}
```

- [ ] **Step 2: Run — expect fail**; **Step 3: Implement**

```python
# src/social_research_probe/llm/host.py
from __future__ import annotations
import json, sys
from typing import Literal, NoReturn

PacketKind = Literal["synthesis", "suggestions", "corroboration"]

def emit_packet(packet: dict, kind: PacketKind) -> NoReturn:
    json.dump({"skill_mode": True, "kind": kind, "packet": packet},
              sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(0)
```

- [ ] **Step 4: Run — expect pass**; **Commit**

```bash
git add src/social_research_probe/llm/ tests/unit/test_llm_host.py
git commit -m "feat(llm/host): skill-mode JSON packet emitter"
```

---

### Task 26: Synthesis formatter sections 1–9 (`synthesize/formatter.py`)

**Files:**
- Create: `src/social_research_probe/synthesize/__init__.py`
- Create: `src/social_research_probe/synthesize/formatter.py`
- Test:   `tests/unit/test_formatter.py`

- [ ] **Step 1: Failing test**

```python
# tests/unit/test_formatter.py
from social_research_probe.synthesize.formatter import build_packet, render_sections_1_9

def test_build_packet_shape():
    items = [{"title":"A","channel":"C","url":"u","source_class":"primary",
              "scores":{"trust":0.9,"trend":0.5,"opportunity":0.4,"overall":0.7},
              "one_line_takeaway":"x"}]
    pkt = build_packet(
        topic="ai agents", platform="youtube",
        purpose_set=["trends"], items_top5=items,
        source_validation_summary={"validated":1,"partially":0,"unverified":0,
                                   "low_trust":0,"primary":1,"secondary":0,
                                   "commentary":0,"notes":""},
        platform_signals_summary="ok",
        evidence_summary="ok",
        stats_summary={"models_run":["descriptive"],"highlights":[],"low_confidence":False},
        chart_captions=[], warnings=[],
    )
    assert pkt["topic"] == "ai agents"
    assert pkt["response_schema"]["compiled_synthesis"].startswith("string")

def test_render_sections_contains_headings():
    out = render_sections_1_9({"topic":"ai","platform":"youtube",
        "purpose_set":["trends"],"items_top5":[],
        "source_validation_summary":{"validated":0,"partially":0,"unverified":0,
            "low_trust":0,"primary":0,"secondary":0,"commentary":0,"notes":""},
        "platform_signals_summary":"-","evidence_summary":"-",
        "stats_summary":{"models_run":[],"highlights":[],"low_confidence":False},
        "chart_captions":[],"warnings":[]})
    for h in ("## 1.", "## 2.", "## 9."):
        assert h in out
```

- [ ] **Step 2: Run — expect fail**; **Step 3: Implement**

```python
# src/social_research_probe/synthesize/formatter.py
from __future__ import annotations
from typing import Any

RESPONSE_SCHEMA = {
    "compiled_synthesis": "string ≤150 words",
    "opportunity_analysis": "string ≤150 words",
}

def build_packet(*, topic: str, platform: str, purpose_set: list[str],
                 items_top5: list[dict], source_validation_summary: dict,
                 platform_signals_summary: str, evidence_summary: str,
                 stats_summary: dict, chart_captions: list[str],
                 warnings: list[str]) -> dict:
    return {
        "topic": topic, "platform": platform, "purpose_set": purpose_set,
        "items_top5": items_top5,
        "source_validation_summary": source_validation_summary,
        "platform_signals_summary": platform_signals_summary,
        "evidence_summary": evidence_summary,
        "stats_summary": stats_summary,
        "chart_captions": chart_captions,
        "warnings": warnings,
        "response_schema": RESPONSE_SCHEMA,
    }

def _fmt_item(i: int, it: dict) -> str:
    s = it.get("scores", {})
    return (f"{i}. **{it['title']}** — {it['channel']} — {it['url']}\n"
            f"   class={it.get('source_class','?')} "
            f"trust={s.get('trust',0):.2f} trend={s.get('trend',0):.2f} "
            f"opportunity={s.get('opportunity',0):.2f} overall={s.get('overall',0):.2f}\n"
            f"   > {it.get('one_line_takeaway','')}")

def render_sections_1_9(packet: dict[str, Any]) -> str:
    svs = packet["source_validation_summary"]
    items = packet["items_top5"]
    stats = packet["stats_summary"]
    warnings = packet.get("warnings", [])
    parts: list[str] = []
    parts.append(f"## 1. Topic & Purpose\n\n{packet['topic']} — "
                 f"purposes: {', '.join(packet['purpose_set'])}")
    parts.append(f"## 2. Platform\n\n{packet['platform']}")
    if items:
        parts.append("## 3. Top Items\n\n" + "\n\n".join(_fmt_item(i+1, it)
                     for i, it in enumerate(items)))
    else:
        parts.append("## 3. Top Items\n\n_(no items returned)_")
    parts.append(f"## 4. Platform Signals\n\n{packet['platform_signals_summary']}")
    parts.append("## 5. Source Validation\n\n"
                 f"- validated: {svs['validated']}, partial: {svs['partially']}, "
                 f"unverified: {svs['unverified']}, low-trust: {svs['low_trust']}\n"
                 f"- primary/secondary/commentary: {svs['primary']}/{svs['secondary']}/{svs['commentary']}"
                 + (f"\n- notes: {svs['notes']}" if svs.get("notes") else ""))
    parts.append(f"## 6. Evidence\n\n{packet['evidence_summary']}")
    models = ", ".join(stats.get("models_run", [])) or "none"
    lc = " (low confidence)" if stats.get("low_confidence") else ""
    highlights = "\n".join(f"- {h}" for h in stats.get("highlights", [])) or "_(no highlights)_"
    parts.append(f"## 7. Statistics\n\nModels: {models}{lc}\n\n{highlights}")
    caps = packet.get("chart_captions", [])
    parts.append("## 8. Charts\n\n" + ("\n".join(f"- {c}" for c in caps) if caps
                                       else "_(no charts rendered)_"))
    parts.append("## 9. Warnings\n\n" + ("\n".join(f"- {w}" for w in warnings)
                                         if warnings else "_(none)_"))
    return "\n\n".join(parts) + "\n"
```

- [ ] **Step 4: Run — expect pass**; **Commit**

```bash
git add src/social_research_probe/synthesize/ tests/unit/test_formatter.py
git commit -m "feat(synthesize): packet builder and sections 1-9 renderer"
```

---

## Phase P2d — Pipeline & Skill-Mode Integration

### Task 27: Pipeline skeleton + CLI wiring (`pipeline.py`)

**Files:**
- Create: `src/social_research_probe/pipeline.py`
- Modify: `src/social_research_probe/cli.py` (add `run-research` subparser)
- Test:   `tests/integration/test_pipeline_skill_mode.py`

- [ ] **Step 1: Failing integration test**

```python
# tests/integration/test_pipeline_skill_mode.py
import json, os, subprocess, sys

def test_run_research_skill_mode_emits_packet(tmp_path):
    env = {**os.environ, "SRP_DATA_DIR": str(tmp_path),
           "PYTHONPATH": "src", "SRP_TEST_USE_FAKE_YOUTUBE": "1"}
    subprocess.run([sys.executable, "-m", "social_research_probe.cli",
                    "update-purposes", "--add", "trends=Track emergence"],
                   check=True, env=env)
    proc = subprocess.run(
        [sys.executable, "-m", "social_research_probe.cli",
         "run-research", "--mode", "skill", "--platform", "youtube",
         '"ai agents"->trends'],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["skill_mode"] is True
    assert payload["kind"] == "synthesis"
    pkt = payload["packet"]
    assert pkt["topic"] == "ai agents"
    assert pkt["platform"] == "youtube"
    assert pkt["purpose_set"] == ["trends"]
    assert "response_schema" in pkt
```

- [ ] **Step 2: Run — expect fail**

```bash
pytest tests/integration/test_pipeline_skill_mode.py -v
```

- [ ] **Step 3: Implement pipeline**

```python
# src/social_research_probe/pipeline.py
from __future__ import annotations
import os
from typing import Literal

from social_research_probe.commands.parse import ParsedRunResearch
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.platforms.base import FetchLimits
from social_research_probe.purposes.registry import load_purposes
from social_research_probe.purposes.merge import merge_purposes
from social_research_probe.validation.source import classify as classify_source
from social_research_probe.scoring.trust import trust_score
from social_research_probe.scoring.trend import trend_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.combine import overall_score
from social_research_probe.synthesize.formatter import build_packet
from social_research_probe.llm.host import emit_packet
from social_research_probe.errors import ValidationError

Mode = Literal["skill", "cli"]

def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import tests.fixtures.fake_youtube  # noqa: F401

_SRC_NUM = {"primary":1.0, "secondary":0.7, "commentary":0.4, "unknown":0.3}

def _score_item(it, sig, h):
    src = classify_source(it, h)
    trust = trust_score(
        source_class=_SRC_NUM[src.value], channel_credibility=0.5,
        citation_traceability=min(1.0, len(h.citation_markers)/3),
        ai_slop_penalty=0.0, corroboration_score=0.3,
    )
    trend = trend_score(
        z_view_velocity=(sig.view_velocity or 0.0),
        z_engagement_ratio=(sig.engagement_ratio or 0.0),
        z_cross_channel_repetition=(sig.cross_channel_repetition or 0.0),
        age_days=30.0,
    )
    opp = opportunity_score(market_gap=0.5, monetization_proxy=0.3,
                            feasibility=0.5, novelty=0.4)
    ov = overall_score(trust=trust, trend=trend, opportunity=opp)
    return ov, {
        "title": it.title, "channel": it.author_name, "url": it.url,
        "source_class": src.value,
        "scores": {"trust": trust, "trend": trend,
                   "opportunity": opp, "overall": ov},
        "one_line_takeaway": (it.text_excerpt or it.title)[:140],
    }

def run_research(cmd: ParsedRunResearch, data_dir, mode: Mode) -> dict:
    _maybe_register_fake()
    purposes = load_purposes(data_dir)["purposes"]
    adapter = get_adapter(cmd.platform, {"data_dir": data_dir})
    if not adapter.health_check():
        raise ValidationError(f"adapter {cmd.platform} failed health check")

    packets: list[dict] = []
    for topic, purpose_names in cmd.topic_map.items():
        for n in purpose_names:
            if n not in purposes:
                raise ValidationError(f"unknown purpose: {n}")
        merged = merge_purposes(purposes, list(purpose_names))
        items = adapter.enrich(adapter.search(topic, FetchLimits()))
        signals = adapter.to_signals(items)
        hints = [adapter.trust_hints(it) for it in items]
        scored = [_score_item(it, s, h) for it, s, h in zip(items, signals, hints, strict=True)]
        scored.sort(key=lambda x: x[0], reverse=True)
        top5 = [d for _, d in scored[:5]]
        svs = {
            "validated": 0, "partially": 0, "unverified": len(top5),
            "low_trust": sum(1 for d in top5 if d["scores"]["trust"] < 0.4),
            "primary": sum(1 for d in top5 if d["source_class"] == "primary"),
            "secondary": sum(1 for d in top5 if d["source_class"] == "secondary"),
            "commentary": sum(1 for d in top5 if d["source_class"] == "commentary"),
            "notes": "",
        }
        packets.append(build_packet(
            topic=topic, platform=cmd.platform,
            purpose_set=list(merged.names),
            items_top5=top5,
            source_validation_summary=svs,
            platform_signals_summary=f"{len(items)} items fetched",
            evidence_summary=("deterministic fixture"
                              if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE")
                              else "live fetch"),
            stats_summary={"models_run": [], "highlights": [], "low_confidence": True},
            chart_captions=[], warnings=[],
        ))

    combined = (packets[0] if len(packets) == 1
                else {"multi": packets,
                      "response_schema": packets[0]["response_schema"]})
    if mode == "skill":
        emit_packet(combined, kind="synthesis")  # exits 0
    return combined
```

- [ ] **Step 4: Wire into `cli.py`**

Add to `_global_parser`:

```python
p_rr = sub.add_parser("run-research")
p_rr.add_argument("--platform", required=True)
p_rr.add_argument("dsl", nargs="+")
```

Add to `_dispatch`:

```python
if args.cmd == "run-research":
    from social_research_probe.commands.parse import parse_command
    from social_research_probe.pipeline import run_research
    raw = f'run-research platform:{args.platform} ' + " ".join(args.dsl)
    run_research(parse_command(raw), data_dir, args.mode)
    return 0
```

- [ ] **Step 5: Run — expect pass**; **Commit**

```bash
git add src/social_research_probe/pipeline.py src/social_research_probe/cli.py tests/integration/test_pipeline_skill_mode.py
git commit -m "feat(pipeline): run-research skill-mode emits valid SkillPacket end-to-end"
```

---

## Verification

Manual smoke (after P2d):

```bash
pip install -e '.[dev]'
srp update-topics --add '"ai agents"'
srp update-purposes --add 'trends=Track emergence across channels'
SRP_TEST_USE_FAKE_YOUTUBE=1 srp run-research --mode skill --platform youtube '"ai agents"->trends'
# Expected: single-line JSON; skill_mode=true, kind=synthesis, packet.topic="ai agents"
```

Automated:

```bash
ruff check .
ruff format --check .
pytest --cov=src --cov-fail-under=85
```

The contract test `tests/contract/test_no_llm_sdk.py` (Task 5) must pass on every commit. CI matrix: Python 3.11 + 3.12.

---

## Follow-on Plans (not in this plan)

- **P3:** `stats/*` (descriptive/growth/regression/correlation/spread/outliers) + `viz/*` selectors and renderers
- **P4:** populate `SocialResearchProbe/references/*.md`; `corroboration/host.py` for skill-mode claim judging
- **P5:** `llm/runners/{claude,gemini,codex,local}.py` + `utils/subprocess_runner.py` (CLI-mode synthesis)
- **P6:** `validation/ai_slop.py` + `validation/claims.py` + `corroboration/{exa,brave,tavily}.py`
- **P7:** second platform adapter (Reddit or TikTok) — contract suite proves zero-core-edit
- **P8:** async fetchers, richer terminal UX, session replay polish






