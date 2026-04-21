#!/usr/bin/env python3
"""Multi-sample judge-LLM reliability evaluator (Phase 10).

Generalized companion to ``eval_summary_quality.py``. Runs N samples via
the configured generator runner, grades each sample with a second
independent judge runner, aggregates per-metric statistics, and applies
reliability gates.

Non-CI. Run nightly or on demand. Writes a timestamped JSON + Markdown
report under ``.srp-eval/<service>/``.

Usage:
    python scripts/eval_llm_quality.py --service summary --runs 5 \\
        --judge-runner claude
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_manifest(service_id: str) -> dict:
    path = (
        REPO_ROOT
        / "tests"
        / "fixtures"
        / "golden"
        / "eval"
        / service_id
        / "manifest.json"
    )
    if not path.exists():
        raise SystemExit(f"no manifest at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize_with_runner(runner_name: str, prompt: str) -> str:
    from social_research_probe.llm.registry import get_runner

    runner = get_runner(runner_name)
    result = runner.run(prompt)
    if isinstance(result, dict):
        # Prefer a 'summary' field; fall back to the first string value.
        if "summary" in result:
            return str(result["summary"])
        for v in result.values():
            if isinstance(v, str):
                return v
        return ""
    return str(result)


def _grade_with_judge(runner_name: str, prompt: str):
    from social_research_probe.evals.judge import parse_judge_reply
    from social_research_probe.llm.registry import get_runner

    runner = get_runner(runner_name)
    raw = runner.run(prompt)
    text = (
        raw["result"]
        if isinstance(raw, dict) and "result" in raw
        else json.dumps(raw)
        if isinstance(raw, dict)
        else str(raw)
    )
    return parse_judge_reply(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--service", required=True, help="service id under golden/eval/")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--judge-runner", default=None, help="runner name for the grader; must differ from generator")
    parser.add_argument("--word-limit", type=int, default=100)
    args = parser.parse_args()

    from social_research_probe.config import load_active_config
    from social_research_probe.evals.harness import (
        evaluate_sample,
        run_reliability_check,
    )
    from social_research_probe.evals.judge import build_judge_prompt
    from social_research_probe.evals.report import (
        timestamp_now,
        write_json,
        write_markdown,
    )
    from social_research_probe.pipeline.enrichment import _build_summary_prompt

    cfg = load_active_config()
    generator_runner = cfg.llm_runner
    if generator_runner == "none":
        raise SystemExit("config.llm_runner is 'none' — cannot run eval")
    if args.judge_runner == generator_runner:
        raise SystemExit(
            f"judge runner must differ from generator runner {generator_runner!r}"
        )

    manifest = _load_manifest(args.service)
    all_samples = []
    for corpus_item in manifest["items"]:
        transcript = (REPO_ROOT / corpus_item["transcript"]).read_text(encoding="utf-8")
        reference = (REPO_ROOT / corpus_item["reference"]).read_text(encoding="utf-8")
        kp_spec = json.loads(
            (REPO_ROOT / corpus_item["keyphrases"]).read_text(encoding="utf-8")
        )
        for i in range(args.runs):
            summary = _summarize_with_runner(
                generator_runner,
                _build_summary_prompt(
                    title=corpus_item.get("title", ""),
                    channel=corpus_item.get("channel", ""),
                    transcript=transcript,
                    word_limit=args.word_limit,
                ),
            )
            judge_scores = None
            if args.judge_runner:
                judge_prompt = build_judge_prompt(summary, reference)
                judge_scores = _grade_with_judge(args.judge_runner, judge_prompt)
            all_samples.append(
                evaluate_sample(
                    summary=summary,
                    transcript=transcript,
                    required_tokens=kp_spec.get("required_tokens", []),
                    allowed_names=kp_spec.get("allowed_proper_nouns", []),
                    target_words=args.word_limit,
                    sample_index=i,
                    judge=judge_scores,
                )
            )

    ts = timestamp_now()
    report = run_reliability_check(
        service_id=args.service,
        timestamp=ts,
        samples=all_samples,
        generator_runner=generator_runner,
        judge_runner=args.judge_runner,
    )
    out_dir = REPO_ROOT / ".srp-eval" / args.service
    json_path = write_json(report, out_dir / f"{ts}.json")
    md_path = write_markdown(
        json.loads(json_path.read_text(encoding="utf-8")),
        out_dir / f"{ts}.md",
    )
    print(f"wrote {json_path.relative_to(REPO_ROOT)}")
    print(f"wrote {md_path.relative_to(REPO_ROOT)}")
    print(f"PASSED: {report.passed}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
