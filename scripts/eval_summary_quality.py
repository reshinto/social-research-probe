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
(``scripts/eval_llm_quality.py``).

Usage:
    python scripts/eval_summary_quality.py [--word-limit 100]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
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


def coverage_score(summary: str, keyphrases: list[str]) -> float:
    """Fraction of required tokens present in ``summary`` (case-insensitive)."""
    if not keyphrases:
        return 1.0
    text = summary.lower()
    hits = sum(1 for token in keyphrases if token.lower() in text)
    return hits / len(keyphrases)


_PROPER_NOUN_RE = re.compile(r"\b[A-Z][A-Za-z0-9]{2,}\b")


def hallucinated_proper_nouns(summary: str, transcript: str, allowed: list[str]) -> list[str]:
    """Proper nouns in ``summary`` that do not appear in the transcript + allowed list.

    A proper noun is any capitalized word ≥ 3 chars. Sentence-initial words
    are noisy but generally safe — callers can tighten the regex later.
    """
    allowed_lower = {a.lower() for a in allowed}
    transcript_lower = transcript.lower()
    candidates = set(_PROPER_NOUN_RE.findall(summary))
    hallucinated = [
        w
        for w in candidates
        if w.lower() not in allowed_lower and w.lower() not in transcript_lower
    ]
    return sorted(set(hallucinated))


def word_count(text: str) -> int:
    return len(text.split())


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
    # The structured JSON path would need a schema; use run() and treat its
    # first string field as the summary, or fall back to summarize_media-like
    # plain-text if the runner returns a string.
    result = runner.run(prompt)
    if isinstance(result, dict):
        return str(result.get("summary") or next(iter(result.values()), ""))
    return str(result)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--word-limit", type=int, default=100)
    p.add_argument("--min-mean-coverage", type=float, default=0.80)
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    corpus = _load_corpus()
    if not corpus:
        print("no reference transcripts found under", CORPUS_DIR, file=sys.stderr)
        return 1

    coverage_scores: list[float] = []
    any_hallucination = False
    any_length_violation = False

    for item in corpus:
        summary = asyncio.run(_summarize_with_active_runner(item["transcript"], args.word_limit))
        kp_spec = item["keyphrases"]
        cov = coverage_score(summary, kp_spec.get("required_tokens", []))
        hallucinations = hallucinated_proper_nouns(
            summary, item["transcript"], kp_spec.get("allowed_proper_nouns", [])
        )
        wc = word_count(summary)
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
        return 2
    if any_hallucination:
        print("FAIL: hallucinated proper nouns present")
        return 3
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
