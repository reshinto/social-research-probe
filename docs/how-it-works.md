[Back to docs index](README.md)


# How It Works

![Research sequence](diagrams/research-sequence.svg)

The research path starts in `cli/parsers.py`, enters `commands/research.py`, then calls `platforms/orchestrator.py`. The orchestrator loads purposes, builds `PipelineState`, and invokes the selected platform pipeline from `PIPELINES`.

## YouTube Stage Order

`YouTubePipeline.stages()` returns ordered stage groups. A group with one stage runs sequentially. A group with multiple stages runs through `asyncio.gather`.

| Order | Stage group | Reads | Writes |
| --- | --- | --- | --- |
| 1 | `fetch` | topic and platform config | `fetch.items`, `fetch.engagement_metrics` |
| 2 | `classify` | fetched items | classified items and updated fetch output |
| 3 | `score` | fetch output and merged purpose weights | `score.all_scored`, `score.top_n` |
| 4 | `transcript`, `stats`, `charts` | scored items | transcripts, stats summary, chart results |
| 5 | `comments` | transcript top-N | comment-enriched top-N |
| 6 | `summary` | comments top-N | text surrogates and summaries |
| 7 | `claims` | summary top-N | extracted claims per item |
| 8 | `corroborate` | claims top-N | corroboration status per claim |
| 9 | `narratives` | corroborated claims | narrative clusters |
| 10 | `synthesis` | narratives, corroboration, score, fetch, stats, charts | synthesis text |
| 11 | `assemble` | accumulated stage outputs | report dictionary |
| 12 | `structured_synthesis` | report dictionary | structured report sections |
| 13 | `report`, `narration` | report dictionary | HTML path and optional audio |
| 14 | `export` | report dictionary | export paths |
| 15 | `persist` | report dictionary and config | SQLite row ids and DB path |

## Failure Model

`BaseTechnology.execute()` checks the technology flag, uses the cache when allowed, catches exceptions, and returns `None` on disabled or failed work. `BaseService.execute_one()` converts technology outputs into `TechResult` records. Stages then decide whether missing output means an empty result, a fallback, or a skipped downstream field.

This is why a run can still produce rankings, statistics, charts, and a basic report when transcripts, LLM runners, or corroboration providers are unavailable.

## Mental Model

A run is not one long function. It is a state machine over `PipelineState`:

```text
CLI args -> ParsedRunResearch -> PipelineState -> named stage outputs -> report -> exports -> SQLite
```

When debugging, find the stage that first lost the data. Then inspect that stage's service and technology adapters.
