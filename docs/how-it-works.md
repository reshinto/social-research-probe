[Back to docs index](README.md)

# How It Works

A research run starts with `srp research` and ends with a report path or local serve command. Internally, the command becomes a parsed command object, then a `PipelineState`, then a sequence of stage outputs. The same shape is intended to work for multiple platforms: the first implemented platform is YouTube, but scoring, analysis, synthesis, reporting, cache, and config are shared concepts.

![Research data flow](diagrams/data-flow.svg)

## One run in plain English

1. The CLI parses the topic and purpose names.
2. The orchestrator loads purposes, merges the selected purpose definitions, and builds platform config.
3. The platform pipeline fetches items and engagement metrics. Today this is the YouTube adapter.
4. The scorer ranks items by trust, trend, opportunity, and overall score.
5. Transcript fetching, statistics, and chart rendering run in parallel.
6. The summary service summarizes the transcript-enriched top-N items when an LLM runner is available.
7. Corroboration checks extracted claims through healthy configured providers.
8. Synthesis and assembly build the report dictionary.
9. Reporting writes Markdown, HTML, chart PNGs, and optional narration.

The topic is the subject being investigated. The purpose is the lens used to interpret that subject. For example, the same topic can be researched as `latest-news`, `trend-analysis`, or `risk-review`; the platform fetch may start from similar search results, but the ranking and final narrative should emphasize different evidence.

![Runtime sequence](diagrams/research-sequence.svg)

## Why the order matters

Fetch and score happen before expensive enrichment. That lets the project spend transcript, LLM, and corroboration work on the most relevant items instead of every search result.

Statistics and charts use the scored dataset and can run without LLM access. This gives a usable analytical report even when runner CLIs or paid providers are unavailable.

This order also makes failures easier to understand. If transcript fetching fails, the user can still inspect fetched items, scores, statistics, and charts. If an LLM runner is not configured, the system can still produce a report with local evidence and empty generated sections rather than losing the whole run.

## Failure model

Most technology calls are isolated. A transcript provider, chart renderer, LLM runner, or corroboration backend can fail without forcing the whole process to crash. Failed technology calls become empty outputs or unsuccessful `TechResult` entries, and later stages use the best available data.

![Parallel stage fan-out](diagrams/async-fanout.svg)

When a run looks incomplete, read it stage by stage. First confirm that candidate items were fetched. Then check whether scoring produced top-ranked items. After that, inspect transcript, summary, corroboration, charts, and report stages. This mirrors how the pipeline is built and avoids debugging the final report before knowing which upstream stage supplied missing data.

## Example mental model

Imagine the topic is `"AI agents"` and the purpose is `"latest-news"`.

| Stage | What it contributes |
| --- | --- |
| Fetch | Candidate platform items about AI agents. |
| Score | A ranked list based on the configured purpose and available features. |
| Enrich | Extra text and metadata for the strongest items. |
| Summarize | Short item-level summaries when a runner is available. |
| Corroborate | External evidence checks for extracted claims. |
| Analyze | Statistics and charts that explain the shape of the result set. |
| Synthesize | Human-readable sections that combine evidence and caveats. |
| Report | Markdown, HTML, chart files, and optional derived outputs. |

If you understand those stages, you can usually diagnose any run. Missing charts point to analysis or rendering. Missing summaries point to transcript or runner configuration. Weak final synthesis points to missing source text, weak summaries, or limited corroboration evidence.
