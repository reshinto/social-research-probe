# LLM reliability harness

[← Documentation hub](README.md)

The reliability harness is `srp`'s answer to "how do we test LLM quality
when the output is non-deterministic?" It runs nightly (or on demand),
samples the configured generator runner N times per corpus item, grades
each sample with a second independent judge runner, aggregates metrics,
and enforces **variance gates** on top of mean gates. Reports land as
timestamped JSON + Markdown under `.srp-eval/<service>/`.

## Purpose

Deterministic evidence tests (the `tests/unit/evidence/` suite) catch formula
drift, schema changes, routing bugs, and other scaffolding regressions.
They cannot catch semantic regressions: summaries losing coherence,
drifting into filler, or hallucinating new proper nouns. Those issues
only appear when a real LLM runs end-to-end — but LLM outputs vary
between calls, so a single pass can't tell a regression from normal
variation.

The harness solves this by:

1. Requiring **multiple samples per item** so variance is observable.
2. Using an **independent judge runner** so we're not asking the model
   to grade its own work.
3. Asserting **both** a mean floor (`≥ 0.80` coverage) and a variance
   ceiling (`≤ 0.10` stdev). Performance drops _and_ consistency drops
   both fail the gate.

## Objective

Ship summaries (and, later, any LLM-backed service) that meet these
reliability targets:

| Gate | Threshold | Rationale |
| --- | --- | --- |
| `mean_coverage_min` | ≥ 0.80 | Summary must carry most key facts. |
| `stdev_coverage_max` | ≤ 0.10 | Quality must be consistent, not lucky. |
| `hallucinations_max` | 0 | Zero tolerance for invented proper nouns. |
| `min_faithfulness` | ≥ 4 (1-5) | Judge must agree summary is faithful. |
| `length_compliance_min` | 1.0 | 100% of samples within word budget. |

## Methodology

![Reliability harness flow](diagrams/reliability-harness.svg)

*(Mermaid source: [docs/diagrams/src/reliability-harness.mmd](diagrams/src/reliability-harness.mmd).
Regenerate with `mmdc -i docs/diagrams/src/reliability-harness.mmd -o docs/diagrams/reliability-harness.svg`.)*

### Per-sample metrics (deterministic)

- `coverage`: fraction of the corpus item's required keyphrases
  present in the summary (case-insensitive substring match).
- `hallucinated_names`: capitalized tokens in the summary that are
  neither in the source transcript nor in the corpus item's allowed
  list. Any proper noun not in the source is treated as hallucinated.
- `length_ok`: word count ∈ `[target - 5, target]`.

### Judge metrics (LLM-graded, 1-5 rubric)

When a judge runner is configured and differs from the generator:

- **faithfulness** — every summary claim supported by the reference;
  any hallucination caps at 2.
- **completeness** — summary captures the reference's key facts.
- **clarity** — reads naturally, no broken sentences.
- **conciseness** — dense, no padding or redundancy.

The judge prompt asks for JSON; `parse_judge_reply` handles markdown
fences, validates scores are integers in `[1, 5]`, and returns `None`
for malformed replies so the harness degrades gracefully to
deterministic-only gates.

### Aggregation & gates

Metrics are aggregated across every sample (across every corpus item ×
N runs): `mean`, `stdev`, `min`, `max`, `p5`, `p95`. Gates then check:

- Coverage has a mean floor AND a stdev ceiling.
- Hallucinations and length are zero-tolerance (the _max_ and _min_
  matter, not the mean).
- Faithfulness uses a floor-of-min, not a mean — one bad sample fails
  the run.

## Reliability gates — full table

| Gate | Threshold | Where checked | Why it's there |
| --- | --- | --- | --- |
| `mean_coverage_min` | 0.80 | `aggregate` + `>=` | Average-case quality floor. |
| `stdev_coverage_max` | 0.10 | `aggregate` + `<=` | Catches quality drift even when the mean looks OK. |
| `hallucinations_max` | 0 | `max(len(hallucinations))` | Any invented name is a release-blocker. |
| `length_compliance_min` | 1.0 | fraction of samples passing | Word budget must hold on every sample. |
| `min_faithfulness` | 4 | `min` across judge outputs | Judge says summary is faithful; one bad sample fails the build. |

## Results

The first nightly run produces baseline numbers. Run locally:

```bash
python scripts/eval_llm_quality.py --service summary --runs 5 \
    --judge-runner claude
```

The command writes `.srp-eval/summary/<timestamp>.{json,md}`. The
Markdown report has a **Gate outcomes** table (green check / red
cross per gate) and **Per-sample outcomes** section with coverage,
hallucinations, length compliance, and per-axis judge scores for
every sample.

## Samples

Here's a hand-picked worked example matching the tech-talk corpus item.

**Transcript excerpt** (full in `tests/fixtures/golden/transcripts/sample_tech_talk.vtt`):
> Today I'm going to walk through how Anthropic's Claude 3.5 Sonnet
> handles extended thinking on complex reasoning tasks. We'll cover
> three benchmarks: GSM8K, MMLU, and HumanEval. Claude 3.5 Sonnet
> scores 96.4% on GSM8K, 88.7% on MMLU, and 92% on HumanEval when
> extended thinking is enabled…

**Candidate summary** (what the redesigned prompt produces):
> Anthropic's Claude 3.5 Sonnet uses extended thinking with a 64,000-token
> scratchpad before producing the final answer. On GSM8K it scores 96.4%,
> on MMLU 88.7%, and on HumanEval 92%. The approach resembles OpenAI's
> o1 but is trained for faithful chain-of-thought. Target audience: ML
> engineers evaluating reasoning models for production workloads where
> correctness beats latency.

**Aggregate report (example numbers; actuals vary per run):**
```
coverage: mean=0.92  stdev=0.04  min=0.83  max=1.00
hallucinations: max=0
length_compliance: 1.0
judge.faithfulness: min=5  mean=5.0
judge.completeness: min=4  mean=4.6
```

All gates pass.

## How to add a new evaluated service

1. **Pick a service id**, e.g. `corroboration-synthesis`.
2. Create `tests/fixtures/golden/eval/<service_id>/manifest.json` listing
   the corpus items. Each item points at:
   - a reference input (the transcript / claim / whatever the service
     consumes).
   - a reference output (the hand-written gold).
   - a keyphrases JSON with `required_tokens` and `allowed_proper_nouns`.
3. Extend `scripts/eval_llm_quality.py` if the new service's invocation
   differs from the `run(prompt) → dict` pattern. Most won't.
4. Run: `python scripts/eval_llm_quality.py --service <id> --runs 5 \
       --judge-runner <name>`.
5. Commit the initial baseline report so future drift is comparable.

## Judge runner selection rules

1. **Judge ≠ Generator** — enforced by the CLI with `SystemExit` if you
   pass `--judge-runner claude` while `config.llm_runner` is also
   `claude`. Prevents self-grading bias.
2. **Optional judge** — if you omit `--judge-runner`, the harness runs
   in deterministic-only mode. The `min_faithfulness` gate is not
   evaluated (it's simply absent from the report), and the run is
   considered passing if the other gates hold.
3. **Judge failure is not a run failure** — if the judge runner fails
   or its reply fails to parse, that sample's judge score is recorded
   as `None` and the deterministic gates still apply.

## Non-goals

- **Not a real-time guardrail.** The harness runs nightly or on demand,
  not in the critical path of a research session. Use deterministic
  evidence tests + pipeline sanity checks for production safety.
- **Not a replacement for the evidence suite.** Deterministic tests in
  `tests/unit/evidence/` are still the primary safety net; the harness adds
  a semantic dimension on top.
- **Not a cross-runner quality comparison tool.** The judge runs within
  one run; for A/B between providers, use it N times with different
  `config.llm_runner` settings and diff the reports.

## See also

- [docs/summary-quality-report.md](summary-quality-report.md) —
  the concrete failure-mode diagnosis that motivated the Phase 9
  prompt redesign.
- [docs/llm-runners.md](llm-runners.md) — runner capability matrix,
  including who supports agentic search + who can grade.
- [docs/how-it-works.md](how-it-works.md) — where summaries (and other
  LLM-backed stages) fit in the pipeline.
