[Back to docs index](README.md)

# Cost Optimization

![Cost flow](diagrams/cost_flow.svg)

The project avoids spending LLM or provider calls until cheaper work has narrowed the candidate set. This matters because research runs can touch several costly operations: platform API calls, transcript retrieval, LLM summaries, external search providers, and optional audio generation.

The default philosophy is "fetch enough, score locally, enrich selectively." Cheap local work should reduce the number of items that need paid or slow work.

## Cost controls

| Control | Where | Effect |
| --- | --- | --- |
| `max_items` | `platforms.youtube.max_items` | Limits fetched candidates. |
| `enrich_top_n` | `platforms.youtube.enrich_top_n` | Limits transcript, summary, and corroboration work. |
| Cache TTLs | `utils/caching/pipeline_cache.py` | Reuses search, transcript, summary, corroboration, and analysis results. |
| Technology gates | `[technologies]` | Disable expensive or unavailable providers. |
| `llm.runner = "none"` | `[llm]` | Runs without LLM-generated sections. |
| `SRP_DISABLE_CACHE=1` | environment | Forces refresh for benchmarking or debugging. |

## Recommended defaults

Start with `enrich_top_n = 5`, `corroboration.provider = "auto"`, and only the provider secrets you actually want to pay for. Raise `max_items` when recall matters; lower `enrich_top_n` when cost or runtime matters.

For quick exploration, keep `max_items` moderate and `enrich_top_n` low. For a final report, raise `max_items` first so the ranking has more candidates, then raise `enrich_top_n` only if you need more transcript summaries and claim checks. If you raise both at once, cost and runtime can grow quickly.

## Main tradeoff

Caching and top-N selection make runs cheaper and faster. They also mean results are a snapshot of the configured search window, ranking formula, and cache freshness.

Use `SRP_DISABLE_CACHE=1` when debugging freshness, provider behavior, or benchmarking. Do not use it by default for normal work: it removes the main protection against repeated provider calls.

## Practical recipes

| Situation | Suggested settings | Why |
| --- | --- | --- |
| First look at a topic | Lower `max_items`, `enrich_top_n = 3`, LLM optional. | Fast and cheap, enough to see if the topic is worth deeper work. |
| Report draft | Default `max_items`, `enrich_top_n = 5`, one corroboration provider. | Balanced evidence depth without checking every candidate. |
| High-recall investigation | Higher `max_items`, default `enrich_top_n`, cache enabled. | More candidates for ranking while still limiting expensive enrichment. |
| Offline/local run | `llm.runner = "none"`, provider gates off. | Produces local scores, stats, charts, and basic reports without external model calls. |
