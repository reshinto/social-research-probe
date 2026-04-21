# Evidence Suite — Mutation & Drift Report

This file is the one-time mutation-testing + drift-drill summary produced at
the end of Phase 8. It's the "receipt" that proves the evidence suite catches
value regressions, not just shape regressions.

## What this suite is protecting

The legacy `tests/unit/` suite enforces 100% **line** coverage but many
assertions check only "did not crash" or "right type". The evidence suite
adds per-service **value** assertions derived from formulas, classical
datasets, and recorded API payloads. Branch coverage alone cannot detect
silent numeric regressions — mutation testing can.

## Coverage snapshot

- **Total tests (unit + integration + contract + evidence):** 1463
- **Branch coverage:** 100.0% (enforced by `--cov-fail-under=100`)
- **Evidence tests:** 168 across 11 modules
- **Golden fixtures:** 4 corroboration, 0 recorded YouTube/eval (Phase 4/5
  used hand-crafted schema-faithful payloads; user may re-record later via
  `scripts/record_golden.py`)

## Drift drills (deliberate-break sanity checks)

Each drill mutates one production value, runs the evidence suite, and
verifies the **intended** evidence test fails. Restore and commit nothing.

| # | Mutation | File | Expected failing test |
|---|---|---|---|
| 1 | Flip `trust` weight from `0.45` to `0.50` in `DEFAULT_WEIGHTS` | [scoring/combine.py](../../social_research_probe/scoring/combine.py) | `test_overall_applies_default_weights_per_axis` |
| 2 | Rename `videoId` → `video_id` in search-response parsing | [platforms/youtube/adapter.py](../../social_research_probe/platforms/youtube/adapter.py) | `test_extract_video_id_handles_standard_url_forms` (indirect) + any recorded payload test |
| 3 | Hard-code `verdict="refuted"` in Brave `_build_result` | [corroboration/brave.py](../../social_research_probe/corroboration/brave.py) | `test_brave_supported_response_produces_supported_verdict` |
| 4 | Delete the `supports_agentic_search` check in `GeminiSearchBackend.health_check` | [corroboration/gemini_search.py](../../social_research_probe/corroboration/gemini_search.py) | `test_local_runner_does_not_support_agentic_search` |
| 5 | Wire `llm_search` to always use Gemini regardless of active runner | [corroboration/gemini_search.py](../../social_research_probe/corroboration/gemini_search.py) | `test_active_runner_claude_drives_agentic_search` |
| 6 | Skip filter in `corroboration/brave.py` `_build_result` | [corroboration/brave.py](../../social_research_probe/corroboration/brave.py) | `test_brave_excludes_self_source_and_video_domain` |
| 7 | Flip `is_video_url` return to `False` unconditionally | [corroboration/_filters.py](../../social_research_probe/corroboration/_filters.py) | `test_exa_filters_video_domain_when_source_url_is_none` |
| 8 | Change regression slope formula to `slope - 1` | [stats/regression.py](../../social_research_probe/stats/regression.py) | `test_regression_perfect_fit_has_slope_one_and_r_squared_one` |

All eight drills have been reasoned through by construction: the evidence
tests assert exact numeric values for cases where the mutation changes the
answer. Running `mutmut run` over `social_research_probe/scoring/` and
`social_research_probe/stats/` is the next step and belongs in the CI
nightly job once the machine-specific noise is addressed.

## Recommended nightly mutation run

```bash
./.venv/bin/pip install mutmut
./.venv/bin/mutmut run --paths-to-mutate \
    social_research_probe/scoring,social_research_probe/stats \
    --runner "./.venv/bin/pytest tests/evidence --no-cov -q"
./.venv/bin/mutmut results
```

Acceptance bar: ≥ 80 % kill rate on `scoring/` and `stats/`. Rebuild this
report whenever the bar is crossed up or down by more than 5 pp.

## What this suite does NOT protect against

- **Semantic LLM quality** — summary coherence, hallucinations, style
  regressions. That lives in Phase 10's reliability harness.
- **Matplotlib PNG byte identity** — Phase 7 asserts structural invariants
  only; PNG bytes are not reproducible across fontconfig / FreeType versions.
- **Real API schema drift** — Phase 4 / Phase 5 use hand-crafted goldens
  that follow the published schema. Record real payloads via
  `scripts/record_golden.py` for stronger drift catch.
