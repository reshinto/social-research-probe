"""Semantic LLM reliability harness.

Phase 10 of the evidence-suite plan. Addresses the hard question: how do
we test LLM output quality when the output is non-deterministic?

Answer: multi-sample aggregation with both **deterministic metrics**
(coverage, hallucination count, length compliance) and a **judge-LLM
rubric** from a second, independent runner. Reliability gates assert on
mean floors *and* variance ceilings so the harness catches both quality
drops and consistency drops.

This package is non-CI — it runs nightly (or on demand) via
``scripts/eval_llm_quality.py``. The deterministic scaffolding
(aggregation math, gate logic, judge fallback) is evidence-tested in
``tests/evidence/test_eval_harness.py``.

Public API:
    run_reliability_check(service_id, corpus_dir, runs, judge_runner)
    EvalReport — the return type
    apply_gates(report, gates) — pass/fail decision
"""

from social_research_probe.evals.harness import (
    EvalReport,
    SampleOutcome,
    apply_gates,
    default_gates,
    run_reliability_check,
)

__all__ = [
    "EvalReport",
    "SampleOutcome",
    "apply_gates",
    "default_gates",
    "run_reliability_check",
]
