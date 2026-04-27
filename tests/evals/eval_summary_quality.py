#!/usr/bin/env python3
"""Real-LLM summary-quality evaluator (nightly, not CI).

Runs the **active configured LLM runner** over the reference corpus under
``tests/fixtures/golden/transcripts/`` and reports key-phrase coverage and
hallucination counts.

Acceptance thresholds (exit-non-zero below):
- mean key-phrase coverage ≥ 0.80 across the corpus
- zero hallucinated proper nouns across all samples
- every output within [word_limit - 5, word_limit] words

This is the Phase 9 companion to the deterministic coverage test. For
multi-sample variance tracking, see the Phase 10 reliability harness
(``tests/evals/eval_llm_quality.py``).

Usage:
    python tests/evals/eval_summary_quality.py [--word-limit 100]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS_DIR = REPO_ROOT / "tests" / "fixtures" / "golden" / "transcripts"


def _load_corpus() -> list[dict]:
    """Discover reference pairs by filename convention."""
    items: list[dict] = []
    for vtt in sorted(CORPUS_DIR.glob("*.vtt")):
        ref = vtt.with_suffix(".reference.md")
        kp = vtt.with_suffix(".keyphrases.json")
        if not ref.exists() or not kp.exists():
            continue
        items.append(
            {
                "name": vtt.stem,
                "transcript": vtt.read_text(encoding="utf-8"),
                "keyphrases": json.loads(kp.read_text(encoding="utf-8")),
            }
        )
    return items


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--word-limit", type=int, default=100)
    p.add_argument("--min-mean-coverage", type=float, default=0.80)
    return p.parse_args()


async def _summarize_with_active_runner(transcript: str, word_limit: int) -> str:
    """Ask the configured runner for a summary. Imports lazily so --help is fast."""
    from social_research_probe.llm.registry import get_runner
    from social_research_probe.pipeline.enrichment import _build_summary_prompt

    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    if cfg.llm_runner == "none":
        raise SystemExit("config.llm_runner is 'none' — cannot run real-LLM eval")
    runner = get_runner(cfg.llm_runner)
    prompt = _build_summary_prompt(
        title="Corpus transcript",
        channel="test",
        transcript=transcript,
        word_limit=word_limit,
    )
    result = runner.run(prompt)
    if isinstance(result, dict):
        return str(result.get("summary") or next(iter(result.values()), ""))
    return str(result)


def main() -> int:
    from tests.evals.metrics import coverage, hallucinated_names

    args = _parse_args()
    corpus = _load_corpus()
    if not corpus:
        print("no reference transcripts found under", CORPUS_DIR, file=sys.stderr)
        return EXIT_NO_CORPUS

    coverage_scores: list[float] = []
    any_hallucination = False
    any_length_violation = False

    for item in corpus:
        summary = asyncio.run(_summarize_with_active_runner(item["transcript"], args.word_limit))
        kp_spec = item["keyphrases"]
        cov = coverage(summary, kp_spec.get("required_tokens", []))
        hallucinations = hallucinated_names(
            summary, item["transcript"], kp_spec.get("allowed_proper_nouns", [])
        )
        wc = len(summary.split())
        length_ok = (args.word_limit - 5) <= wc <= args.word_limit

        coverage_scores.append(cov)
        if hallucinations:
            any_hallucination = True
        if not length_ok:
            any_length_violation = True

        print(f"[{item['name']}] coverage={cov:.2f} words={wc} hallucinations={hallucinations}")

    mean_cov = sum(coverage_scores) / len(coverage_scores)
    print(f"\nmean coverage: {mean_cov:.3f}")
    print(f"any hallucination: {any_hallucination}")
    print(f"any length violation: {any_length_violation}")

    if mean_cov < args.min_mean_coverage:
        print(f"FAIL: mean coverage {mean_cov:.3f} below {args.min_mean_coverage:.2f}")
        return EXIT_COVERAGE_FAIL
    if any_hallucination:
        print("FAIL: hallucinated proper nouns present")
        return EXIT_HALLUCINATION_FAIL
    print("PASS")
    return EXIT_SUCCESS


EXIT_SUCCESS = 0
EXIT_NO_CORPUS = 1
EXIT_COVERAGE_FAIL = 2
EXIT_HALLUCINATION_FAIL = 3


if __name__ == "__main__":
    raise SystemExit(main())
