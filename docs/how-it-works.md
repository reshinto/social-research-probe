[Back to docs index](README.md)

# How It Works

A research run starts with `srp research` and ends with a report path or a local `srp serve-report --report ...` command. Internally, command parsing produces a `ParsedRunResearch`, the orchestrator builds a `PipelineState`, and the platform pipeline publishes named stage outputs until the final report dictionary is ready.

![Research data flow](diagrams/data-flow.svg)

## One YouTube Run

1. **Parse**: `commands/research.py` parses `[platform] TOPIC PURPOSES`. If the platform is omitted, it uses `all`; with the current registry, `all` runs YouTube.
2. **Resolve purposes**: `platforms/orchestrator.py` loads saved purposes and merges selected purpose methods, evidence priorities, and scoring overrides.
3. **Fetch**: `YouTubeFetchStage` calls `YouTubeSourcingService`, which uses YouTube search, hydration, and engagement technologies.
4. **Classify**: `YouTubeClassifyStage` labels channels as `primary`, `secondary`, `commentary`, or `unknown`.
5. **Score**: `YouTubeScoreStage` ranks items by trust, trend, opportunity, and overall score.
6. **Parallel analysis group**: transcripts, statistics, and charts run after scoring. Transcripts enrich top-N items; statistics and charts use the scored dataset.
7. **Comments**: `YouTubeCommentsStage` fetches comments for the configured number of top videos.
8. **Summary**: `YouTubeSummaryStage` builds a text surrogate, then asks the configured LLM runner for item summaries when LLM use is enabled.
9. **Claims**: `YouTubeClaimsStage` extracts structured claims from the best available text.
10. **Corroborate**: `YouTubeCorroborateStage` checks claims through healthy configured providers.
11. **Narratives**: `YouTubeNarrativesStage` clusters related claims into narrative groups.
12. **Synthesis**: `YouTubeSynthesisStage` produces free-form synthesis when a runner is available.
13. **Assemble**: `YouTubeAssembleStage` merges stage outputs into the report packet and computes warnings.
14. **Structured synthesis**: `YouTubeStructuredSynthesisStage` attaches structured report sections.
15. **Report and narration**: HTML/Markdown writing and optional audio narration run together.
16. **Export**: `YouTubeExportStage` writes sources, comments, claims, narratives, methodology, and run-summary artifacts next to the HTML report.
17. **Persist**: `YouTubePersistStage` writes the completed run to the local SQLite database when enabled.

![Runtime sequence](diagrams/research-sequence.svg)

## Why The Order Matters

Fetch, classification, and scoring happen before expensive enrichment. That lets `srp` spend transcript, comment, LLM, corroboration, and persistence work on the items most likely to matter.

Statistics and charts can run without an LLM runner. You can still get ranked items, aggregate stats, PNG charts, and basic reports with `llm.runner = "none"`.

Claims and narratives run after summaries and text surrogates because they need the best available source text. Corroboration runs after claims because it needs specific, checkable claim text instead of broad video titles whenever possible.

## Failure Model

Most external or expensive work is isolated behind `BaseTechnology.execute()` and `BaseService.execute_batch()`. A failed provider usually becomes `None`, an empty output, or an unsuccessful `TechResult` rather than crashing the whole run.

![Parallel stage fan-out](diagrams/async-fanout.svg)

Debug missing output stage by stage:

| Missing output | Check first |
| --- | --- |
| No fetched items | YouTube API key, query, `platforms.youtube.max_items`, and `stages.youtube.fetch`. |
| Weak ranking | Source classification, engagement metrics, scoring weights, and item normalization. |
| No transcripts | `--no-transcripts`, transcript stage/service/technology gates, captions availability, `yt-dlp`, and Whisper. |
| No summaries or synthesis | `llm.runner`, runner binary availability, runner technology gate, and timeout. |
| No corroboration | `corroboration.provider`, provider secrets, `max_claims_per_item`, and `services.corroborate.corroboration`. |
| No charts | `charts/` output dir, chart service/technology gates, and whether scored items exist. |
| No exports | HTML report path and `platforms.youtube.export.enabled`. |
| No database rows | `[database].enabled`, `services.persistence.sqlite`, and `stages.youtube.persist`. |

## Mental Model

Think of `PipelineState` as a shared notebook for one run. Each stage reads earlier entries and writes a small named entry:

```text
fetch -> classify -> score -> transcript/stats/charts -> comments -> summary
-> claims -> corroborate -> narratives -> synthesis -> assemble
-> structured_synthesis -> report/narration -> export -> persist
```

If you understand that sequence, most changes become local. New source-specific fetching belongs in a platform stage. A reusable task belongs in a service. A provider call or pure algorithm belongs in a technology. Cross-cutting helpers belong in `utils`.
