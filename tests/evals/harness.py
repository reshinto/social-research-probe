"""Reliability harness — multi-sample aggregation with gates.

See ``docs/llm-reliability-harness.md`` (Phase 11) for the full methodology.
This module provides the pure orchestration logic; tests/evals/eval_llm_quality.py
is the CLI entry point that wires real runners into it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .judge import JudgeScores
from .metrics import (
    aggregate,
    coverage,
    hallucinated_names,
    length_compliance,
)


@dataclass
class SampleOutcome:
    """Per-run metrics for one corpus item across one sampling pass."""

    sample_index: int
    summary: str
    coverage: float
    hallucinations: list[str]
    length_ok: bool
    judge: JudgeScores | None = None


@dataclass
class Gate:
    """A single reliability threshold that must hold across all samples."""

    name: str
    threshold: float
    observed: float
    passed: bool


@dataclass
class EvalReport:
    """Structured result of ``run_reliability_check``."""

    service_id: str
    timestamp: str
    runs: int
    generator_runner: str
    judge_runner: str | None
    samples: list[SampleOutcome] = field(default_factory=list)
    aggregates: dict[str, dict[str, float]] = field(default_factory=dict)
    gates: list[Gate] = field(default_factory=list)
    passed: bool = False


def default_gates() -> dict[str, float]:
    """Return the built-in reliability thresholds (service-agnostic)."""
    return {
        "mean_coverage_min": 0.80,
        "stdev_coverage_max": 0.10,
        "hallucinations_max": 0,
        "min_faithfulness": 4,
        "length_compliance_min": 1.0,
    }


def evaluate_sample(
    *,
    summary: str,
    transcript: str,
    required_tokens: list[str],
    allowed_names: list[str],
    target_words: int,
    sample_index: int,
    judge: JudgeScores | None = None,
) -> SampleOutcome:
    """Compute deterministic metrics + wrap optional judge scores."""
    return SampleOutcome(
        sample_index=sample_index,
        summary=summary,
        coverage=coverage(summary, required_tokens),
        hallucinations=hallucinated_names(summary, transcript, allowed_names),
        length_ok=length_compliance(summary, target_words),
        judge=judge,
    )


def apply_gates(
    samples: list[SampleOutcome],
    gates: dict[str, float],
) -> tuple[list[Gate], bool]:
    """Evaluate every gate and return (gate_results, all_passed)."""
    cov_values = [s.coverage for s in samples]
    cov_stats = aggregate(cov_values)
    max_hallucinations = max((len(s.hallucinations) for s in samples), default=0)
    length_compliance_fraction = (
        sum(1 for s in samples if s.length_ok) / len(samples) if samples else 0.0
    )
    judged = [s.judge for s in samples if s.judge is not None]
    min_faithfulness = min(j.faithfulness for j in judged) if judged else None

    results: list[Gate] = []

    results.append(
        Gate(
            name="mean_coverage_min",
            threshold=gates["mean_coverage_min"],
            observed=cov_stats["mean"],
            passed=cov_stats["mean"] >= gates["mean_coverage_min"],
        )
    )
    results.append(
        Gate(
            name="stdev_coverage_max",
            threshold=gates["stdev_coverage_max"],
            observed=cov_stats["stdev"],
            passed=cov_stats["stdev"] <= gates["stdev_coverage_max"],
        )
    )
    results.append(
        Gate(
            name="hallucinations_max",
            threshold=gates["hallucinations_max"],
            observed=float(max_hallucinations),
            passed=max_hallucinations <= gates["hallucinations_max"],
        )
    )
    results.append(
        Gate(
            name="length_compliance_min",
            threshold=gates["length_compliance_min"],
            observed=length_compliance_fraction,
            passed=length_compliance_fraction >= gates["length_compliance_min"],
        )
    )
    if min_faithfulness is not None:
        results.append(
            Gate(
                name="min_faithfulness",
                threshold=gates["min_faithfulness"],
                observed=float(min_faithfulness),
                passed=min_faithfulness >= gates["min_faithfulness"],
            )
        )

    passed = all(g.passed for g in results)
    return results, passed


def run_reliability_check(
    *,
    service_id: str,
    timestamp: str,
    samples: list[SampleOutcome],
    generator_runner: str,
    judge_runner: str | None,
    gates: dict[str, float] | None = None,
) -> EvalReport:
    """Assemble an :class:`EvalReport` from pre-collected samples.

    Real-runner execution lives in ``tests/evals/eval_llm_quality.py``. This
    function takes already-computed samples so it is trivially unit-testable
    (no subprocess, no LLM calls).
    """
    gate_spec = gates or default_gates()
    cov_stats = aggregate([s.coverage for s in samples])
    gate_results, passed = apply_gates(samples, gate_spec)
    return EvalReport(
        service_id=service_id,
        timestamp=timestamp,
        runs=len(samples),
        generator_runner=generator_runner,
        judge_runner=judge_runner,
        samples=samples,
        aggregates={"coverage": cov_stats},
        gates=gate_results,
        passed=passed,
    )
