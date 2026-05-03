[Back to docs index](README.md)


# Objective

The project turns social-media search results into a local, auditable research packet. The source code is optimized for evidence handling rather than free-form chat: every run produces structured stage outputs, rankings, optional claims and corroboration, report files, exports, and optional database rows.

## What The Code Optimizes For

| Goal | Implementation |
| --- | --- |
| Repeatable command-line operation | `srp` is the console script in `pyproject.toml`; parsing lives in `cli/parsers.py`. |
| Platform isolation | `platforms/youtube` owns YouTube-specific stage order. |
| Cost control | Stage gates, service gates, technology gates, top-N enrichment, and cache. |
| Evidence auditability | `PipelineState.outputs`, CSV exports, methodology export, run-summary JSON, SQLite schema. |
| Partial progress | Technologies return `None` on failure; services wrap outputs in `TechResult` and `ServiceResult`. |

## Current Scope

The concrete platform is YouTube. The `all` platform key is a meta-pipeline that runs every concrete platform in `PIPELINES`. Since the only concrete key is `youtube`, `all` currently means YouTube.

The pipeline can use YouTube Data API, transcript APIs, yt-dlp, Whisper, LLM runner CLIs, corroboration search providers, chart rendering, HTML rendering, Voicebox or macOS narration, export writers, and SQLite persistence. Each optional dependency is behind a technology flag.

## Non-Goals In The Source

The code does not attempt to be a database-first analytics warehouse. SQLite persistence is the final stage, not the pipeline's working memory. The code also does not embed vendor model SDKs for generated text; it uses runner CLIs and local wrappers through adapter classes.
