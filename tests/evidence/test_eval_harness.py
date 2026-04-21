"""Evidence tests — reliability harness scaffolding (CI-safe).

Phase 10 of the evidence-suite plan. These tests verify the harness logic
works correctly with **canned data** (no real LLM invocation). The full
real-runner behaviour is exercised via ``scripts/eval_llm_quality.py``
nightly.

The reliability harness's **methodology**:

1. Sample the generator runner N times per corpus item.
2. Compute deterministic metrics per sample:
   - coverage (fraction of required keyphrases present)
   - hallucinated proper nouns (names not in source/allowed)
   - length compliance (word count within ±tolerance of target)
3. Ask an independent judge runner for a 1-5 rubric per axis
   (faithfulness, completeness, clarity, conciseness). Judge ≠ generator
   is **required**; when only one runner is configured, judge is skipped
   and only deterministic metrics run — reported clearly in output.
4. Aggregate metrics across samples (mean, stdev, min, max, p5, p95).
5. Apply gates — **all** must pass to ship:
   - mean(coverage) ≥ 0.80
   - stdev(coverage) ≤ 0.10  (consistency floor, not just mean floor)
   - max(hallucinations) = 0
   - min(faithfulness) ≥ 4  (when judge ran)
   - length_compliance_fraction = 1.0 (every sample fits word budget)
6. Report pass/fail + timestamped JSON/Markdown for trend tracking.

Evidence receipt:

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| metrics.coverage | 4 required, 3 present | 0.75 | fraction formula |
| metrics.hallucinated_names | name absent from source | flagged | regex + set diff |
| metrics.length_compliance | 97 words, target=100, tol=5 | True | band check |
| metrics.aggregate | [0.9, 0.95, 0.85] | mean≈0.9 stdev>0 | statistics stdlib |
| judge.parse_judge_reply | canned JSON | JudgeScores dict | JSON parse |
| judge.parse_judge_reply | malformed text | None | fail-safe |
| apply_gates | 5 samples, coverage mean 0.85 stdev 0.05 | pass | all gates hold |
| apply_gates | 5 samples, one with hallucination | fail | zero-tolerance |
| apply_gates | 5 samples, high-variance coverage | fail | stdev gate catches drift |
| run_reliability_check | full report assembly | EvalReport.passed reflects gates | orchestration |
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from social_research_probe.evals.harness import (
    SampleOutcome,
    apply_gates,
    default_gates,
    evaluate_sample,
    run_reliability_check,
)
from social_research_probe.evals.judge import (
    JudgeScores,
    build_judge_prompt,
    parse_judge_reply,
)
from social_research_probe.evals.metrics import (
    aggregate,
    coverage,
    hallucinated_names,
    length_compliance,
)
from social_research_probe.evals.report import (
    timestamp_now,
    write_json,
    write_markdown,
)

# ---------------------------------------------------------------------------
# metrics — pure math building blocks
# ---------------------------------------------------------------------------


def test_coverage_returns_exact_fraction():
    assert coverage("a b c", ["a", "b", "c", "d"]) == 0.75
    assert coverage("", []) == 1.0
    assert coverage("nothing matches", ["XYZ"]) == 0.0


def test_hallucinated_names_flags_capitalized_tokens_not_in_source():
    transcript = "Anthropic released a new model."
    summary = "Anthropic's model was praised by DeepMind."
    hallucinations = hallucinated_names(summary, transcript, allowed=["Anthropic"])
    assert "DeepMind" in hallucinations
    assert "Anthropic" not in hallucinations


def test_length_compliance_band_inclusive():
    assert length_compliance("one " * 100, target_words=100, tolerance=5) is True
    assert length_compliance("one " * 95, target_words=100, tolerance=5) is True
    assert length_compliance("one " * 94, target_words=100, tolerance=5) is False
    assert length_compliance("one " * 101, target_words=100, tolerance=5) is False


def test_aggregate_returns_zeros_for_empty_input():
    stats = aggregate([])
    assert stats == {
        "mean": 0.0,
        "stdev": 0.0,
        "min": 0.0,
        "max": 0.0,
        "p5": 0.0,
        "p95": 0.0,
    }


def test_aggregate_single_value_sets_stdev_to_zero():
    stats = aggregate([0.7])
    assert stats["mean"] == 0.7
    assert stats["stdev"] == 0.0
    assert stats["min"] == stats["max"] == 0.7


def test_aggregate_multiple_values_matches_stdlib():
    import statistics

    values = [0.8, 0.85, 0.9, 0.95, 1.0]
    stats = aggregate(values)
    assert stats["mean"] == pytest.approx(statistics.mean(values))
    assert stats["stdev"] == pytest.approx(statistics.stdev(values))
    assert stats["min"] == 0.8
    assert stats["max"] == 1.0


# ---------------------------------------------------------------------------
# judge — prompt building + reply parsing
# ---------------------------------------------------------------------------


def test_build_judge_prompt_includes_rubric_axes_and_instructions():
    prompt = build_judge_prompt("candidate summary", "reference summary")
    for axis in ("faithfulness", "completeness", "clarity", "conciseness"):
        assert axis in prompt
    assert "REFERENCE" in prompt
    assert "CANDIDATE" in prompt


def test_parse_judge_reply_accepts_plain_json():
    raw = (
        '{"faithfulness": 5, "completeness": 4, "clarity": 5, '
        '"conciseness": 4, "justification": "faithful and dense"}'
    )
    scores = parse_judge_reply(raw)
    assert scores is not None
    assert scores.faithfulness == 5
    assert scores.completeness == 4


def test_parse_judge_reply_strips_markdown_fences():
    raw = (
        "```json\n"
        '{"faithfulness": 3, "completeness": 3, "clarity": 3, '
        '"conciseness": 3, "justification": "ok"}\n'
        "```"
    )
    scores = parse_judge_reply(raw)
    assert scores is not None
    assert scores.faithfulness == 3


def test_parse_judge_reply_returns_none_for_malformed_text():
    assert parse_judge_reply("not json at all") is None
    assert parse_judge_reply('{"faithfulness": "five"}') is None
    assert (
        parse_judge_reply(
            '{"faithfulness": 99, "completeness": 1, "clarity": 1, "conciseness": 1, "justification": ""}'
        )
        is None
    )


def test_parse_judge_reply_returns_none_for_json_list():
    """JSON that isn't a dict (e.g. a list) must not crash the caller."""
    assert parse_judge_reply("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# apply_gates — reliability thresholds
# ---------------------------------------------------------------------------


def _good_sample(i: int, coverage_val: float = 0.9) -> SampleOutcome:
    return SampleOutcome(
        sample_index=i,
        summary="ok",
        coverage=coverage_val,
        hallucinations=[],
        length_ok=True,
        judge=JudgeScores(5, 5, 5, 5, "good"),
    )


def test_apply_gates_passes_when_all_samples_are_good():
    samples = [_good_sample(i, 0.85) for i in range(5)]
    results, passed = apply_gates(samples, default_gates())
    assert passed is True
    assert all(g.passed for g in results)


def test_apply_gates_fails_when_any_sample_hallucinates():
    samples = [_good_sample(i, 0.9) for i in range(5)]
    samples[2].hallucinations = ["SomeMadeUpCorp"]
    results, passed = apply_gates(samples, default_gates())
    assert passed is False
    assert any(g.name == "hallucinations_max" and not g.passed for g in results)


def test_apply_gates_fails_when_coverage_variance_too_high():
    """Mean coverage passes the floor but stdev exceeds the consistency ceiling."""
    coverage_values = [0.95, 0.85, 0.65, 0.95, 0.85]
    samples = [_good_sample(i, c) for i, c in enumerate(coverage_values)]
    results, passed = apply_gates(samples, default_gates())
    assert passed is False
    assert any(g.name == "stdev_coverage_max" and not g.passed for g in results)


def test_apply_gates_fails_when_any_judge_faithfulness_is_low():
    samples = [_good_sample(i, 0.9) for i in range(5)]
    samples[0].judge = JudgeScores(2, 5, 5, 5, "flagged a hallucination")
    _, passed = apply_gates(samples, default_gates())
    assert passed is False


def test_apply_gates_skips_faithfulness_gate_when_no_judge_scores():
    """When judge step was skipped (single-runner config), the gate doesn't
    fail the run — the min_faithfulness gate is simply not evaluated."""
    samples = [
        SampleOutcome(
            sample_index=i,
            summary="ok",
            coverage=0.9,
            hallucinations=[],
            length_ok=True,
            judge=None,
        )
        for i in range(5)
    ]
    results, passed = apply_gates(samples, default_gates())
    assert passed is True
    assert not any(g.name == "min_faithfulness" for g in results)


# ---------------------------------------------------------------------------
# run_reliability_check — full report assembly
# ---------------------------------------------------------------------------


def test_run_reliability_check_returns_passing_report_for_good_samples():
    samples = [_good_sample(i, 0.9) for i in range(5)]
    report = run_reliability_check(
        service_id="summary",
        timestamp="2026-04-21T12:00:00Z",
        samples=samples,
        generator_runner="gemini",
        judge_runner="claude",
    )
    assert report.passed is True
    assert report.runs == 5
    assert report.aggregates["coverage"]["mean"] == pytest.approx(0.9)


def test_run_reliability_check_returns_failing_report_for_bad_samples():
    samples = [_good_sample(i, 0.5) for i in range(5)]
    report = run_reliability_check(
        service_id="summary",
        timestamp="2026-04-21T12:00:00Z",
        samples=samples,
        generator_runner="gemini",
        judge_runner="claude",
    )
    assert report.passed is False


def test_evaluate_sample_wraps_deterministic_metrics():
    outcome = evaluate_sample(
        summary="Claude scored 96.4 on GSM8K.",
        transcript="Claude scored 96.4 on GSM8K.",
        required_tokens=["Claude", "96.4", "GSM8K"],
        allowed_names=["Claude", "GSM8K"],
        target_words=100,
        sample_index=0,
    )
    assert outcome.coverage == 1.0
    assert outcome.hallucinations == []


# ---------------------------------------------------------------------------
# report writers
# ---------------------------------------------------------------------------


def test_write_json_and_markdown_emit_files(tmp_path):
    samples = [_good_sample(i, 0.9) for i in range(3)]
    report = run_reliability_check(
        service_id="summary",
        timestamp="test-ts",
        samples=samples,
        generator_runner="gemini",
        judge_runner="claude",
    )
    json_path = write_json(report, tmp_path / "report.json")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["service_id"] == "summary"
    assert payload["passed"] is True
    assert len(payload["samples"]) == 3

    md_path = write_markdown(payload, tmp_path / "report.md")
    md = md_path.read_text(encoding="utf-8")
    assert "Reliability eval" in md
    assert "| Gate | Threshold | Observed | Result |" in md


def test_write_markdown_handles_missing_gates_and_judge(tmp_path):
    """Covers the false branches: empty gates list + sample without judge."""
    payload = {
        "service_id": "summary",
        "timestamp": "ts",
        "runs": 1,
        "generator_runner": "gemini",
        "judge_runner": None,
        "gates": [],
        "samples": [
            {
                "coverage": 0.9,
                "hallucinations": [],
                "length_ok": True,
                "judge": None,
            }
        ],
    }
    md_path = write_markdown(payload, tmp_path / "bare.md")
    text = md_path.read_text(encoding="utf-8")
    assert "Reliability eval" in text
    # No gates table header when gates are empty.
    assert "| Gate |" not in text
    # No judge line when judge is None.
    assert "Judge:" not in text


def test_timestamp_now_returns_sortable_utc_string():
    ts = timestamp_now()
    # Format: YYYYMMDDTHHMMSSZ → length 16, ends with Z.
    assert len(ts) == 16
    assert ts.endswith("Z")


# ---------------------------------------------------------------------------
# Manifest integrity
# ---------------------------------------------------------------------------


def test_eval_corpus_manifest_points_at_real_fixtures():
    manifest = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "fixtures"
            / "golden"
            / "eval"
            / "summary"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    repo_root = Path(__file__).resolve().parent.parent.parent
    for item in manifest["items"]:
        for key in ("transcript", "reference", "keyphrases"):
            assert (repo_root / item[key]).exists(), f"missing {item[key]}"
