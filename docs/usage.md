# Usage Guide

[Home](README.md) → Usage

This guide covers running research, understanding the output, and tuning the pipeline. For installation and secret setup see [Installation](installation.md). For every flag and config key see [Commands](commands.md).

---

## Your first research run

```bash
srp research "AI safety" "latest-news"
```

`srp` will:
1. Query YouTube for recent "AI safety" videos
2. Score and rank them by credibility and trend signals
3. Fetch transcripts and generate LLM summaries for the top 5
4. Corroborate the top claims with web-search APIs
5. Run statistical analysis across all results
6. Print a Markdown summary to stdout and write an HTML report

The terminal shows progress as each stage completes:

```
[srp] fetching youtube: AI safety / latest-news
[srp] scored 20 items
[srp] enriching top 5 with transcripts…
[srp] corroborating via exa…
[srp] running statistical analysis…
[srp] HTML report: file:///~/.social-research-probe/reports/ai-safety_latest-news_20260420.html
```

---

## Understanding the output

### Stdout — Markdown summary

After the run, `srp` prints a structured Markdown document with 9 or 11 sections:

| Section | What it contains |
|---|---|
| 1. Topic & Purpose | The topic searched and the research intent applied |
| 2. Platform | Which platform adapter was used |
| 3. Top Items | The 5 highest-scoring videos — title, channel, score, and a transcript summary |
| 4. Platform Signals | Aggregate view velocity, credibility spread, and content-type breakdown |
| 5. Source Validation | Channel credibility assessment for the top-5 sources |
| 6. Evidence | Summary of corroboration results from web-search APIs |
| 7. Statistics | Highlights from the 15+ statistical models (regression coefficients, cluster structure, etc.) |
| 8. Charts | Paths to the rendered PNG chart files |
| 9. Warnings | Any data quality flags (low result count, missing transcripts, etc.) |
| 10. Compiled Synthesis | Plain-English LLM synthesis of what was found *(requires `llm.runner` configured)* |
| 11. Opportunity Analysis | Actionable LLM-generated recommendations *(requires `llm.runner` configured)* |

Sections 10–11 appear only when an LLM runner is configured. Without one they show:
```
_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_
```

### HTML report

The full report is written to:
```
~/.social-research-probe/reports/<topic-slug>-<platform>-<YYYYMMDD-HHMMSS>.html
```

For example: `ai-safety-youtube-20260420-183000.html`

Each run creates a **new file** — old reports are never overwritten. Open the file in any browser. It is self-contained — all charts are embedded and it includes a built-in text-to-speech player. The HTML report is the authoritative document; the stdout Markdown is a quick inline summary.

### Chart PNGs

Charts are saved to `~/.social-research-probe/charts/` with fixed filenames:

```
~/.social-research-probe/charts/
├── overall_score_bar.png
├── overall_score_by_rank_line.png
├── overall_score_histogram.png
├── trust_vs_opportunity_regression.png
├── trust_vs_trend_regression.png
├── trust_vs_opportunity_scatter.png
├── trust_vs_trend_scatter.png
├── feature_correlations_heatmap.png
├── overall_by_rank_residuals.png
└── top5_summary_table.png
```

**Charts are overwritten on every run.** If you need to preserve charts from a specific run, either copy them out of the directory or use the HTML report — the HTML embeds all charts at generation time and is not affected by later runs.

### JSON packet

The raw structured output is also printed to stdout as a JSON envelope:
```json
{
  "kind": "synthesis",
  "packet": { ... }
}
```

The packet contains every field used to render the report (scores, summaries, evidence, statistics, chart paths). Use it to pipe results to other tools or to regenerate the HTML report with custom synthesis sections via `srp report`.

---

## Core concepts

### Topics

A topic is a search subject registered in `~/.social-research-probe/topics.json`. Using registered topics lets you compare runs over time with consistent terminology.

```bash
srp show-topics
srp update-topics --add "climate tech"
srp update-topics --remove "old-topic"
```

### Purposes

A purpose defines the research intent — it shapes how queries are enriched and how results are weighted. For example, `"latest-news"` prioritises recency; `"emerging-research"` prioritises academic credibility.

```bash
srp show-purposes
srp update-purposes --add "emerging-research"="Track peer-reviewed preprints"
```

### Pending proposals

`suggest-topics` and `suggest-purposes` use the configured LLM runner to generate proposals. Proposals sit in a queue and do not take effect until you accept them — so the LLM cannot change your taxonomy without review.

```bash
srp suggest-topics
srp show-pending
srp apply-pending      # accept all
srp discard-pending    # reject all
```

---

## Running research

### Single topic + purpose
```bash
srp research "AI agents" "latest-news"
```

### Multiple purposes
```bash
srp research "AI agents" "latest-news,trends"
```

### Natural-language query
When the argument is a full sentence, `srp` classifies it into a topic and purpose automatically. Requires `llm.runner != none`.
```bash
srp research "who is winning the LLM benchmarks race?"
```

### Excluding YouTube Shorts
```bash
srp research "AI agents" "latest-news" --no-shorts
```

---

## Controlling the number of videos

| Setting | Default | Effect |
|---|---|---|
| `platforms.youtube.max_items` | `20` | How many videos are fetched and scored |
| `platforms.youtube.recency_days` | `90` | Only return videos from the last N days |
| `platforms.youtube.enrich_top_n` | `5` | How many top-scored videos get transcripts + LLM summaries + corroboration |

By default, the top **5** scored videos receive full enrichment. You can widen both the candidate pool (`max_items`) and the enrichment budget (`enrich_top_n`) independently:

```bash
srp config set platforms.youtube.max_items 50    # wider candidate pool
srp config set platforms.youtube.recency_days 30 # recent content only
srp config set platforms.youtube.enrich_top_n 10 # enrich the top 10 instead of 5
```

**Tradeoffs:**
- `max_items` adds cheap API metadata fetches — negligible cost to raise.
- `enrich_top_n` adds per-item transcript download + LLM summary + corroboration calls — the dominant cost of a research run. A run with `enrich_top_n = 20` takes roughly 4× longer than the default and uses 4× the LLM tokens.

---

## Corroboration modes

| Mode | When to use |
|---|---|
| `host` (default) | Auto-uses all backends whose API keys are configured |
| `exa` / `brave` / `tavily` | Force a single backend |
| `llm_cli` | No external search key — uses the LLM runner instead |
| `none` | Disable corroboration entirely |

```bash
srp config set corroboration.backend llm_cli   # no search API needed
srp config set corroboration.backend none      # skip corroboration
```

---

## Regenerating a report

To attach new synthesis sections to an existing packet without re-running research:

```bash
srp report \
  --packet ~/.social-research-probe/packets/my-packet.json \
  --synthesis-10 /tmp/s10.txt \
  --synthesis-11 /tmp/s11.txt \
  --out ~/Desktop/report.html
```

---

## Claude Code skill

After `srp install-skill`, use `srp` from inside Claude Code:

```
/srp research "AI safety" "latest-news"
```

The skill runs the CLI, parses the JSON packet, and formats sections 1–9 as a chat message. The HTML report path is surfaced so you can open it directly from the chat.

---

## See also

- [Commands](commands.md) — every flag, config key, and exit code
- [Installation](installation.md) — API keys, LLM runner setup, verification
- [Architecture](architecture.md) — how the pipeline works internally
