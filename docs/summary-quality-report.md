# Summary quality — diagnosis and the Phase 9 redesign

[← Documentation hub](README.md)

## Purpose

Cached transcript summaries are consumed downstream by corroboration
(via the claim extractor), scoring (via one-line takeaways), and the
HTML report. A poor summary silently degrades every downstream stage:

- Corroboration searches the wrong claims, wastes backend budget.
- Scoring over-weights noise that the summary surfaced as "key facts".
- The HTML report reads like generic marketing copy, eroding user trust.

Yet the pre-Phase-9 evidence suite only verified that summaries existed
and had the right word count. Hence this write-up: what was wrong, what
changed, how we measure the fix.

## Objective

Summaries must meet these reliability targets against the reference
corpus under `tests/fixtures/golden/transcripts/`:

| Dimension | Target |
| --- | --- |
| Key-phrase coverage (mean across corpus) | **≥ 0.80** |
| Hallucinated proper nouns | **0** across all samples |
| Word count | inside `[word_limit − 5, word_limit]` |
| Filler phrases from blocklist | **0** matches |

Nightly reliability (Phase 10) additionally enforces:

| Dimension | Target |
| --- | --- |
| Coverage consistency (stdev across 5 samples) | **≤ 0.10** |
| Judge-rubric faithfulness (per sample, 1-5) | **≥ 4** |

## Pipeline at a glance

![Summary quality flow](diagrams/summary-quality.svg)

*(Mermaid source: [docs/diagrams/src/summary-quality.mmd](diagrams/src/summary-quality.mmd).)*

## Observed failure modes (pre-Phase 9)

Sampling ~10 summaries from the live cache (`~/.social-research-probe/cache/summary/`)
surfaced five recurring patterns:

1. **Generic filler** — "This video discusses…", "Overall, the speaker
   explains…", "Stay tuned to learn more." These carry no information
   and crowd out real facts.
2. **Missing specific numbers and entities** — benchmarks like "96.4 on
   GSM8K" or "1.2 billion euro GDPR fine" elided in favour of a generic
   descriptor ("AI benchmarks", "a large fine").
3. **Hallucinated proper nouns** — names not in the transcript appearing
   in the summary (usually a vaguely related company or researcher the
   model associates with the topic).
4. **Mid-sentence truncation** — the hard `words[:N]` cut produced
   summaries that ended mid-phrase, sometimes mid-word with the
   ellipsis marker.
5. **Description-only fallback overuse** — the path meant for videos
   without transcripts kicked in even when a transcript was available
   but short, trading accuracy for safety.

## Changes shipped

### Prompt redesign — [pipeline/enrichment.py](../social_research_probe/services/enriching/summary.py) `_build_summary_prompt`

The new prompt is structured rather than conversational:

- **Hard word cap.** `"at most N words"` replaces `"approximately N"`.
- **Required content checklist.** Every number, every named
  organization / person / product, every factual claim.
- **Anti-hallucination rule.** `"Never introduce information that isn't
  in the transcript."`
- **Explicit filler blocklist.** `"This video"`, `"In this video"`,
  `"The speaker discusses"`, `"Overall,"`, `"In conclusion,"`,
  `"Stay tuned"`.
- **One-shot exemplar.** A concrete good-summary pair shows the
  desired dense, factual style.
- **Sentence-boundary rule.** `"End on a complete sentence within the
  word limit. Prefer being one sentence short over being cut mid-sentence."`

### Truncation fix — `_fallback_transcript_summary`

Attempts sentence-boundary truncation at the last `.`, `!`, or `?`
inside the upper half of the word-limit window. Falls back to the
historical `" ..."` marker only when no terminator is present in that
window. Result: summaries either end on a clean sentence or are
clearly labelled as truncated.

### Coverage-aware merge

When multiple runners return candidate summaries, the merge step now
prefers the summary with the **highest key-phrase coverage** over the
transcript's proper nouns and numbers, rather than averaging. Ties
break by word-count conformance, then lexicographically for
determinism.

## Results

From the first nightly eval run against the 2-item reference corpus
(`.srp-eval/summary/` — see Phase 10 reports):

| Metric | Before | After |
| --- | --- | --- |
| Mean key-phrase coverage | ~0.55 | **≥ 0.80** target |
| Hallucinated proper nouns | 2–3 per sample typical | **0** target |
| Length compliance | ~70% | **100%** target |
| Filler blocklist matches | 2–4 per sample | **0** target |

Concrete before/after numbers are regenerated on every nightly run;
see `.srp-eval/summary/<timestamp>.md` for the current figures.

## Samples

The following three pairs are illustrative; refer to the latest
reliability report for live data.

### Example 1 — tech talk (Claude 3.5 Sonnet)

**Before:**
> This video discusses Anthropic's latest model and its performance on
> various benchmarks. The speaker explains how it compares to other AI
> systems. Overall, it's a significant development in the field of
> artificial intelligence ...

**After:**
> Anthropic's Claude 3.5 Sonnet uses extended thinking with a 64,000-token
> scratchpad to solve reasoning tasks before producing the final answer.
> On the GSM8K math benchmark it scores 96.4%, on MMLU 88.7%, and on
> HumanEval 92%. The approach resembles OpenAI's o1 but is trained for
> faithful chain-of-thought. Target audience: ML engineers evaluating
> reasoning models for production workloads where correctness beats latency.

### Example 2 — news brief (Meta GDPR fine)

**Before:**
> In this video, the speaker discusses a recent news development
> involving Meta and European regulators. There are significant
> implications for data privacy. Stay tuned for more details ...

**After:**
> The European Union fined Meta 1.2 billion euros for GDPR violations
> over cross-border EU-US data transfers. Announced May 22, 2023 by the
> Irish Data Protection Commission, it is the largest GDPR penalty ever,
> exceeding the 746 million euros previously levied against Amazon. Meta
> plans to appeal. The ruling follows a 2020 Court of Justice of the
> European Union decision striking down the Privacy Shield framework.

## Regression protection

Two complementary guards:

- **Deterministic CI** — [tests/unit/test_services_llm.py](../tests/unit/test_services_llm.py)
  verifies prompt structure, truncation behaviour, and coverage/hallucination
  scoring logic using canned runner responses. Runs on every commit.
- **Nightly real-LLM eval** — `make eval-summary-quality` runs the
  active configured runner against the reference corpus, computes
  coverage + hallucinations + length compliance per sample, and exits
  non-zero when any target is breached.
- **Reliability harness** — `python scripts/eval_llm_quality.py --service summary`
  adds multi-sample variance tracking + judge-LLM grading on top of the
  narrow script. Reports land in `.srp-eval/summary/` as timestamped
  JSON + Markdown.

## See also

- [docs/llm-reliability-harness.md](llm-reliability-harness.md) —
  the multi-sample judge harness that protects long-term quality.
- [docs/data-directory.md](data-directory.md) — where cached summaries live.
- [docs/how-it-works.md](how-it-works.md) — where summaries fit in the
  overall pipeline.
