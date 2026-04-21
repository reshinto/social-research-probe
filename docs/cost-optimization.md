# Cost Optimization

[Home](README.md) → Cost Optimization

`srp` is designed so that the **computer does the work and the LLM does the talking**. Every stage that can be computed without an LLM is computed without an LLM. This doc enumerates each technique, where it lives in code, and how to tune it.

---

## The ledger — who spends what

![Cost flow — CPU vs LLM, cache branches, top-N cutoff](diagrams/cost_flow.svg)


A typical run (top-5 of 50 items, corroboration enabled, runner configured):

| Stage | Mechanism | Per-run LLM tokens | CPU cost |
|---|---|---|---|
| Fetch | YouTube Data API v3 | 0 | low |
| Score (trust / trend / opportunity) | [`scoring/`](../social_research_probe/scoring/) — pure Python | 0 | low |
| Transcript — captions | `youtube-transcript-api` / `yt-dlp` | 0 | low |
| Transcript — Whisper fallback | [`platforms/youtube/whisper_transcript.py`](../social_research_probe/platforms/youtube/whisper_transcript.py) — local inference | 0 | high (one-off per video, cached 30 days) |
| Enrichment — 100-word summary | LLM runner | ~1–3 KB × 5 items | negligible |
| Stats (20+ models) | [`stats/`](../social_research_probe/stats/) — scipy + stdlib | 0 | medium |
| Charts (10 types) | [`viz/`](../social_research_probe/viz/) — matplotlib | 0 | low |
| Corroboration | search-API call per top item | 0 on `none`, bounded on host | low |
| Synthesis (sections 10–11) | LLM runner, single call | ~2–5 KB | negligible |

Translation: LLM usage is **bounded by top-N items** (default 5), not by the 50+ items you searched.

---

## Six design levers that keep the bill small

### 1. Top-N cutoff before expensive stages

Only the top N scored items are enriched (transcript + summary) and corroborated. Everything below the cutoff is scored, charted, and counted — but costs nothing extra.

Code: [`pipeline/orchestrator.py`](../social_research_probe/pipeline/orchestrator.py) — `enrich_top_n = int(platform_config.get("enrich_top_n", 5))`.

Tune it via `config.toml`:

```toml
[platforms.youtube]
enrich_top_n = 3   # cheapest
# or
enrich_top_n = 10  # deepest
```

### 2. Captions before Whisper

Transcript enrichment tries free sources first:

1. YouTube's native caption track (free).
2. `yt-dlp --write-auto-sub` (free, community-maintained).
3. Whisper, **only if both fail** (local inference — no cloud cost, but takes seconds to minutes per video).

Code: [`pipeline/enrichment.py`](../social_research_probe/pipeline/enrichment.py) — `_fetch_transcript_with_fallback`.

The Whisper path uses `yt-dlp` to download only the audio track, then feeds it to OpenAI Whisper for transcription. **Whisper decodes that audio via `ffmpeg`**, so `ffmpeg` must be on `$PATH`. The whole chain runs on your machine — no audio is uploaded anywhere. Output is cached for 30 days so the same video is never transcribed twice.

### 3. Aggressive caching with real TTLs

[`utils/pipeline_cache.py`](../social_research_probe/utils/pipeline_cache.py) pins TTLs so expensive work is deduplicated across runs:

| Artifact | TTL | Rationale |
|---|---|---|
| Caption transcripts | 7 days | Videos rarely gain new captions |
| Whisper transcripts | 30 days | Nothing about the audio changes |
| LLM summaries | 7 days | Re-summarising the same transcript is wasteful |
| Corroboration results | 6 hours | Web state shifts, but not minute-to-minute |

Disable it with `SRP_DISABLE_CACHE=1` when debugging.

### 4. Local stats + local charts

The entire `stats/` package runs on `scipy` and the Python stdlib. No stats model calls out to a service. The `viz/` package uses `matplotlib`. Running the analysis twice costs nothing.

If you added one LLM call per chart or per statistic, a single report would run into the tens of thousands of tokens. None of them do.

### 5. Soft failure on optional stages

Every optional integration (corroboration backend, LLM runner, Whisper) can fail without aborting the run. The failure is logged into the report's warnings section; the rest of the pipeline continues. This avoids the "retry storm" pattern where a rate-limit or transient outage fans out into repeated LLM calls.

Code: [`synthesize/warnings.py`](../social_research_probe/synthesize/warnings.py) + the `try/except` guards in [`pipeline/orchestrator.py`](../social_research_probe/pipeline/orchestrator.py).

### 6. Ensemble returns first success

When multiple LLM runners are configured, [`llm/ensemble.py`](../social_research_probe/llm/ensemble.py) fans them out concurrently via `asyncio.gather(..., return_exceptions=True)` and returns as soon as one succeeds. The winner is "whichever worked first," which in practice is **the cheapest configured runner that is healthy right now**.

This means you can list Gemini (free) first, Claude second, and only pay for Claude when Gemini rate-limits you.

---

## Config recipes for different budgets

### Cheapest possible

```toml
[llm]
runner = "gemini"          # free tier via browser auth

[corroboration]
backend = "gemini_search"  # free tier too

[platforms.youtube]
max_items = 20
enrich_top_n = 3
```

Runs under the free Gemini tier for most workloads; Whisper stays on your machine.

### Deepest analysis

```toml
[llm]
runner = "claude"

[corroboration]
backend = "host"           # multi-source: tavily + brave + exa + gemini_search

[platforms.youtube]
max_items = 100
enrich_top_n = 10
```

Pay more, see more.

### Fastest iteration

Set `SRP_FAST_MODE=1` or:

```toml
[features]
fast_mode = true

[platforms.youtube]
max_items = 10
enrich_top_n = 3
```

[`utils/fast_mode.py`](../social_research_probe/utils/fast_mode.py) clamps the top-N and narrows the backend list.

### Fully offline

```toml
[llm]
runner = "local"           # SRP_LOCAL_LLM_BIN points at your binary

[corroboration]
backend = "none"           # skip corroboration entirely
```

Sections 10–11 use placeholders; everything else works.

---

## What happens when things go wrong

- **LLM runner misconfigured** — enrichment summaries + synthesis are skipped; stats and charts still render.
- **Corroboration backend unreachable** — the affected backend is excluded; others continue. If none work, corroboration is skipped with a warning in section 9.
- **Whisper fails** — the item's transcript is empty; its summary falls back to title + description.
- **Cache directory unwritable** — the pipeline runs uncached (no crash) but the next run pays the full cost.

None of these failures cost extra LLM tokens. Fail-soft is a cost optimisation.

---

## See also

- [LLM Runners](llm-runners.md) — which runners exist, why Gemini CLI is the recommended free default
- [Corroboration](corroboration.md) — backend inventory and pricing
- [Configuration](configuration.md) — every config key and its default
- [Architecture](architecture.md) — the layered design that makes these tradeoffs explicit
