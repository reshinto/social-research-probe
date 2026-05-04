[Back to docs index](README.md)


# LLM Reliability Harness

![Reliability harness](diagrams/reliability-harness.svg)

Evaluation code lives under `tests/evals`. It measures runner and claim behavior using fixtures and report helpers rather than live product runs.

## Source Files

| Path | Role |
| --- | --- |
| `tests/evals/harness.py` | Shared evaluation harness. |
| `tests/evals/metrics.py` | Metric calculations. |
| `tests/evals/judge.py` | Judging helpers. |
| `tests/evals/eval_summary_quality.py` | Summary quality evaluation. |
| `tests/evals/eval_llm_quality.py` | LLM output evaluation. |
| `tests/evals/assess_claims_quality.py` | Claim extraction assessment. |
| `tests/fixtures/golden/` | Golden transcripts and corroboration fixtures. |

## When To Run

Run evaluations when changing prompts, schemas, runner adapters, claim extraction, or summary behavior. Unit tests prove code paths; evals help detect quality regressions.
