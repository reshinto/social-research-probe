# Testing

[Home](README.md) → Testing

---

## Philosophy

Tests are written before implementation (TDD). The coverage gate is 100% branch coverage — no production code is merged without a failing test that was watched to fail first.

The `# pragma: no cover` inline comment is banned. Use `exclude_lines` in `pyproject.toml` for genuinely untestable branches (defensive raises, abstract method stubs).

---

## Test Tiers

![Testing pyramid](diagrams/testing-pyramid.svg)

```
tests/
├── unit/        # pure functions, no I/O
├── integration/ # orchestrator + fake adapters, no network
└── contract/    # cross-cutting invariants (version consistency, doc navigation)
```

### Unit tests

Test pure functions in isolation: scoring formulas, z-score, `merge_purposes`, `detect_warnings`, argparse dispatch. No disk I/O, no network, no subprocess.

Run: `pytest tests/unit`

### Integration tests

Test the orchestrator end-to-end with fake adapters registered via environment variables. The pipeline runs fully; only platform API calls and LLM subprocess calls are replaced.

```bash
SRP_TEST_USE_FAKE_YOUTUBE=1 SRP_TEST_USE_FAKE_CORROBORATION=1 pytest tests/integration
```

### Contract tests

Assert cross-cutting invariants that cannot be owned by a single unit:

- `test_version_consistency.py` — `VERSION` file, `pyproject.toml`, and `__version__` all agree.
- `test_docs_diagrams.py` — every SVG under `docs/diagrams/` is referenced by at least one Markdown file.
- `test_docs_navigation.py` — every doc under `docs/` has a breadcrumb link to `docs/README.md` and is reachable from it.

Run: `pytest tests/contract`

---

## Key Fixtures

Defined in `tests/conftest.py`:

| Fixture | Description |
|---|---|
| `tmp_data_dir` | Temporary `Path` set as `$SRP_DATA_DIR`; seeded with minimal topics/purposes registry |
| `fake_youtube` | Sets `SRP_TEST_USE_FAKE_YOUTUBE=1` and imports `tests/fixtures/fake_youtube.py` |
| `fake_corroboration` | Registers fake Exa, Brave, and Tavily backends |

Always use `tmp_data_dir` rather than writing to `~/.social-research-probe` in tests.

---

## Fakes vs Mocks

Prefer registered fake adapters over `monkeypatch`. Fakes implement the real interface (`PlatformAdapter`, `CorroborationBackend`) and exercise the same code path as production. Mocks verify call counts but do not exercise the interface contract.

When monkeypatching is necessary (e.g. patching `Config.load` to return a fixture config), patch the module where the name is looked up, not where it is defined:

```python
# orchestrator calls Config.load — patch it there
monkeypatch.setattr("social_research_probe.pipeline.orchestrator.Config.load", ...)
```

---

## Running Tests

```bash
# Full suite with coverage gate (1500+ tests, ~30 s) — THE gate
pytest -q

# Same run, more verbose coverage output
pytest tests/unit tests/contract tests/evidence \
    --cov=social_research_probe --cov-report=term-missing --cov-fail-under=100

# Integration tests only (no coverage enforcement)
pytest tests/integration --no-cov

# Fast iteration on a single file
pytest tests/unit/test_scoring.py -x -q
```

CI runs all tiers on Python 3.11, 3.12, and 3.13.

> **Important:** The `--cov-fail-under=100` gate applies to **all three
> tiers combined** (unit + contract + evidence). Running any subset in
> isolation under-reports — for example, `pytest tests/unit tests/contract`
> alone hits ~95% because the evidence tier is the only place that covers
> the new `social_research_probe/evals/` package and the per-runner
> `agentic_search` implementations. The distinction between the tiers is
> **purpose** (value vs. line), not whether their tests count toward
> coverage. They all do.

### Evidence suite — running the new tests in `tests/evidence/`

`tests/evidence/` is an additive tier that proves each service produces
the **correct numeric / structural output** for documented inputs (not just
"did not crash"). Every test docstring includes a receipt table of
*input / expected output / why* so a reviewer can trace every assertion
back to a formula, stdlib reference, golden payload, or hand-worked
example.

```bash
# Run only the evidence tier (fast, no network)
make test-evidence
# …equivalent to:
pytest tests/evidence -v --no-cov
```

The Makefile target disables the project-wide `--cov-fail-under=100`
gate because the evidence tier is a narrow slice — running it in
isolation covers only ~43% of lines (it deliberately doesn't exercise
the CLI parsers, command entry points, or state-migration shims, which
live in the unit tier). Full coverage runs against `pytest -q` still
enforce 100%.

> **Why not enforce 100% coverage on `tests/evidence/` alone?** The two
> tiers have different *purposes*, not different counting rules.
> `tests/unit/` + `tests/contract/` exist for **line coverage** — they
> prove every branch is reachable. `tests/evidence/` exists for **value
> coverage** — every test has an *(input / expected / why)* receipt
> proving the scoring formula is right, the stats match a reference,
> the corroboration backend classifies correctly. Both tiers contribute
> to the 100% gate on the combined run; neither hits 100% alone
> (unit+contract misses the new `evals/` package and the per-runner
> `agentic_search` methods, evidence misses the CLI shims). The
> `make test-evidence` shortcut uses `--no-cov` because enforcing a
> coverage number against a narrow slice is misleading, not because
> those tests don't count. If you want fast feedback on value-tier
> assertions while iterating, use `make test-evidence`. If you want the
> gate, run `pytest -q`.

#### LLM quality evaluators (out of CI)

Two scripts exercise real LLM runners against the reference corpus
under `tests/fixtures/golden/transcripts/`. They are **not** part of
the deterministic evidence suite — they require API keys and network
access, so run them locally or in a nightly cron rather than in CI.

```bash
# Phase 9 narrow summary-quality eval (single run per corpus item)
make eval-summary-quality
# …equivalent to:
python scripts/eval_summary_quality.py --word-limit 100

# Phase 10 reliability harness (N samples, optional judge runner)
python scripts/eval_llm_quality.py --service summary --runs 5 \
    --judge-runner claude
```

`eval_llm_quality.py` enforces that `--judge-runner` differs from
`config.llm_runner` (no self-grading) and writes timestamped
JSON + Markdown reports under `.srp-eval/<service>/`. See
[docs/llm-reliability-harness.md](llm-reliability-harness.md) for the
full methodology, gates, and worked examples.

#### Recording goldens with real APIs (optional)

Phase 4/5 corroboration + YouTube goldens ship as hand-crafted
schema-faithful payloads. If you have API keys and want higher-fidelity
replays, re-record them:

```bash
# Example — re-record the Brave "supported" fixture
python scripts/record_golden.py \
    --service brave \
    --url "https://api.search.brave.com/res/v1/web/search?q=GPT-4+release+date" \
    --auth-env SRP_BRAVE_API_KEY \
    --auth-header X-Subscription-Token \
    --out brave_supported.json
```

The recorder redacts `Authorization` / `X-Api-Key` / `X-Subscription-Token`
headers plus email/credit-card-shaped strings before writing the JSON.
See [docs/data-directory.md](data-directory.md) for where data lives
at runtime.

---

## TDD Workflow

1. Write a failing test that names the expected behaviour.
2. Run `pytest path/to/test.py -x -q` and confirm it fails for the right reason.
3. Write the minimum production code to pass.
4. Run `pytest --cov-fail-under=100 --cov-branch` and confirm all green.
5. Refactor under green.

Never skip step 2. A test that passes immediately either tests existing behaviour (wrong test) or is a no-op.

---

## Adding a New Platform Adapter

1. Create `tests/fixtures/fake_<platform>.py` implementing `PlatformAdapter`.
2. Register via `SRP_TEST_USE_FAKE_<PLATFORM>=1` seam (copy the YouTube pattern).
3. Write integration tests using the fake.
4. Write unit tests for the adapter's transform logic.

---

## Adding a New Corroboration Backend

1. Write a failing test for `health_check()` returning `True` and a failing test for the `corroborate()` path.
2. Implement the backend.
3. Write a test for `health_check()` returning `False` (missing secret).
4. Write a test for the `ValidationError` path (bad API response).

---

## Common Pitfalls

| Pitfall | Fix |
|---|---|
| Monkeypatching the wrong module | Patch where the name is used, not where it is defined |
| `asyncio.run` inside `asyncio.to_thread` | Use `async def` test functions with `asyncio_mode = "auto"` |
| Coverage gap after module split | Check that the new module's branches are covered, not just reachable |
| `pragma: no cover` temptation | Use `exclude_lines` in `[tool.coverage.report]` instead |

---

## See also

- [Architecture](architecture.md) — module structure the tests exercise
- [Design Patterns](design-patterns.md) — fake-via-env test seam pattern
- [Python Language Guide](python-language-guide.md) — async test conventions
