[Home](README.md) → How It Works

# How It Works

This page explains what `srp research` actually does, step by step, in plain English. No code knowledge needed.

---

## The short version

`srp` talks to the **YouTube Data API** to get a list of videos matching your topic. It reads their public statistics (views, likes, comments, channel size) — it never downloads or streams any video. It then ranks every video by a composite score, fetches the closed-caption text of the top 5, and sends that text to an LLM to generate summaries. Finally it cross-checks claims against web-search APIs and writes the report.

---

## Stage 1 — Fetch: what data does it actually pull?

`srp` makes **API calls to YouTube**, not HTTP requests to video pages. No video is downloaded, no audio is decoded. YouTube provides a free-to-use Data API that returns structured JSON.

Two things happen:

1. **Search call** — asks YouTube for up to `max_items` (default: 20) recent videos matching your topic. The API returns a list of video IDs plus basic snippet data (title, channel name, publish date, thumbnail URL, short description).

2. **Hydration calls** — with those video IDs in hand, `srp` makes two parallel requests:
   - `videos.list` — returns per-video statistics: view count, like count, comment count, and duration in seconds.
   - `channels.list` — returns per-channel statistics: subscriber count and total video count.

Both hydration calls run at the same time (concurrent) so the combined fetch adds only one round-trip of latency instead of two.

After hydration, each video has: title, channel name, publish date, view count, like count, comment count, channel subscriber count, and duration. That is everything used for scoring.

**Controlling how many videos are fetched:**

```bash
srp config set platforms.youtube.max_items 50    # fetch up to 50 videos (default: 20)
srp config set platforms.youtube.recency_days 30 # only videos from the last 30 days (default: 90)
```

Fetching more videos gives the scoring and statistical models a bigger pool to work from, which improves ranking quality. The tradeoff is a longer fetch time: each batch of ~50 video IDs requires one `videos.list` API call. Fetching 100 videos takes roughly twice as long as fetching 20. The enrichment budget (transcripts and LLM summaries, covered in Stage 3) is a separate setting — see [`enrich_top_n` below](#controlling-how-many-videos-get-enriched).

**Shorts filtering:** If `--no-shorts` is passed, any video under 90 seconds is dropped before scoring. Otherwise Shorts are included.

---

## Stage 2 — Score: how does ranking work?

Every video gets three sub-scores, each in the 0–1 range, then a weighted composite. All maths run on the metadata fetched above — no AI involved at this stage.

### Trust score (how credible is the source?)

```
trust = 0.35 × source_class
      + 0.25 × channel_credibility
      + 0.15 × citation_traceability
      + 0.15 × (1 − ai_slop_penalty)
      + 0.10 × corroboration_score
```

| Component | What it measures | How it is computed |
|---|---|---|
| `source_class` | Is this a primary, secondary, commentary, or unknown source? | Classifier checks channel name and title for markers like "official", "research", "reaction" |
| `channel_credibility` | How established is the channel? | `0.15 × log10(subscriber_count)` — a channel with 1 M subscribers scores ~0.9; 1 000 subscribers scores ~0.45 |
| `citation_traceability` | Does the title/description reference traceable sources? | Count of citation markers divided by 3, capped at 1.0 |
| `ai_slop_penalty` | Does the content look like AI-generated filler? | Raised by the AI slop validator if triggered; defaults to 0 |
| `corroboration_score` | Did web search find supporting sources? | Populated after the corroboration stage; defaults to 0.3 during initial scoring |

### Trend score (how fast is it gaining momentum?)

Trend scoring uses **z-scores** — each video's metrics are compared to the average across all fetched videos for that run, not against some fixed scale. A video is "trending" if it is performing well *relative to the other results*, not in absolute terms.

```
trend = 0.40 × normalised_z(view_velocity)
      + 0.20 × normalised_z(engagement_ratio)
      + 0.20 × normalised_z(cross_channel_repetition)
      + 0.20 × recency_decay
```

| Component | What it measures | How it is computed |
|---|---|---|
| `view_velocity` | Views per day since publish | `view_count / age_days` |
| `engagement_ratio` | How much the audience interacts | `(likes + comments) / views` |
| `cross_channel_repetition` | Is this topic mentioned by multiple channels? | Count of other fetched videos covering the same topic (currently 0 — placeholder for future) |
| `recency_decay` | How recent is the video? | `exp(−age_days / 30)` — a 30-day-old video scores 0.37; a 90-day-old video scores 0.05 |

The `normalised_z` function maps a z-score to a 0–1 value: `clip(0.5 + z / 6)`. A video one standard deviation above average gets ~0.67; one below average gets ~0.33.

### Opportunity score (is there room for more content here?)

```
opportunity = 0.40 × market_gap
            + 0.30 × monetization_proxy
            + 0.20 × feasibility
            + 0.10 × novelty
```

| Component | What it measures | How it is computed |
|---|---|---|
| `market_gap` | Is this topic under-served? | `1 − cross_channel_repetition` — if few channels cover it, there is more room |
| `monetization_proxy` | Is the audience highly engaged? | `clip(engagement_ratio × 20)` — a 5% engagement rate scores 1.0 |
| `feasibility` | How achievable is creating content here? | Fixed at 0.5 in the current implementation (placeholder for future signals) |
| `novelty` | Is this recent enough to still be fresh? | `max(0, 1 − age_days / 180)` — a 6-month-old video scores 0 |

### Overall score (final ranking)

```
overall = 0.45 × trust + 0.30 × trend + 0.25 × opportunity
```

Trust carries the most weight because the tool is designed for evidence-first research. A viral video from an unknown source should not rank above a moderately popular video from a credible institution.

All videos are sorted by `overall` score descending. The top 5 proceed to enrichment.

---

## Stage 3 — Enrich: what happens to the top scored videos?

The highest-scoring videos get more information fetched. This is the only stage that can take more than a few seconds. By default the pipeline enriches the top **5** videos, but this is configurable.

### Controlling how many videos get enriched

```bash
srp config set platforms.youtube.enrich_top_n 10   # enrich the top 10 instead of 5 (default)
```

Implementation: see [social_research_probe/pipeline/orchestrator.py](../social_research_probe/pipeline/orchestrator.py) — the line `top5 = all_scored[:enrich_top_n]` reads this config value. The packet field is still named `items_top5` for backwards compatibility, but the actual count is whatever `enrich_top_n` is set to.

**Why this setting matters:** raising `enrich_top_n` is the biggest way to make a run longer and more expensive. Each enriched item triggers:
- One caption download (fast) or one Whisper audio transcription (slow, CPU-intensive)
- One LLM call to generate a 100-word summary
- Up to `corroboration.max_claims_per_item` web-search API calls during Stage 5

A run with `enrich_top_n = 20` takes roughly 4× longer and uses 4× the LLM tokens compared to the default.

### Transcripts (not video downloads)

`srp` does **not download the video**. It tries to get the text in two ways, in order:

1. **YouTube closed captions** — `yt-dlp` fetches the auto-generated or uploaded caption file (a text file, a few kilobytes). This is fast and requires no audio processing.
2. **Whisper transcription** (fallback) — if no captions are available, `yt-dlp` downloads the audio track only (not the video), and OpenAI Whisper transcribes it locally on your machine. This is slower and uses CPU/GPU. At most 2 videos are transcribed by Whisper simultaneously to prevent memory exhaustion.

If neither source produces a transcript, the video's public description is used instead.

The transcript is trimmed to 6 000 characters before being sent to the LLM.

### LLM summaries

With the transcript (or description) in hand, the LLM ensemble is called to write a 100-word+ summary covering: main topic, key arguments or findings, target audience, and specific claims. The summary becomes the transcript excerpt shown in Section 3 of the report.

All 5 summaries are requested concurrently.

---

## Stage 4 — Analyse: statistics and charts

The 15+ statistical models run on the full set of scored videos (not just the top 5). They look for patterns in the score distributions — whether results cluster into quality tiers, whether trust and trend are correlated, which features drive the overall score. The 10 chart PNGs are rendered from the same data.

No network calls happen in this stage.

---

## Stage 5 — Synthesise: corroboration and report

Specific factual claims are extracted from the top-5 summaries and sent to web-search APIs (Exa, Brave, or Tavily) as queries. The number of supporting or contradicting results is counted and attached to each item.

The LLM ensemble writes Sections 10 and 11 (compiled synthesis and opportunity analysis). The full HTML report is written to disk.

---

## What never happens

- **No video is downloaded for scoring.** Only closed captions or (as a fallback) audio are fetched, and only for the top 5.
- **No video is stored.** Transcripts are kept in memory during the run and written into the report packet. They are not persisted separately.
- **No YouTube account is needed.** All calls use the YouTube Data API with an API key.
- **No YouTube scraping.** Every data point comes from official API responses.

---

## Why these weights?

The weighting choices reflect the tool's purpose:

| Weight | Reason |
|---|---|
| Trust 45% | Evidence-first design: a credible but less viral source beats an unverified viral one |
| Trend 30% | Recency and momentum matter for social media research — stale content is less actionable |
| Opportunity 25% | Useful for content strategy use cases; lower weight since it is less relevant for pure research |
| Trust: source_class 35% | The most directly observable signal of credibility |
| Trust: channel_credibility 25% | Subscriber count is an imperfect but consistent proxy for track record |
| Trend: view_velocity 40% | Views per day is the most direct measure of current momentum |

---

## Why not just ask an LLM?

A common alternative is to skip the API entirely and ask a large language model: *"What are the most credible YouTube videos about AI safety right now?"* This is faster, but has fundamental reliability problems.

### What a pure-LLM approach gets wrong

| Problem | Why it happens |
|---|---|
| **Hallucinated videos** | LLMs generate plausible-sounding titles, channels, and URLs that do not exist. |
| **Frozen in time** | LLM training data has a cutoff. It cannot know what was published last week. |
| **No real metrics** | The LLM has no access to current view counts, engagement rates, or subscriber numbers. It guesses based on what it read during training. |
| **Popularity bias** | The LLM will skew toward well-known creators it saw frequently in training data, not toward whoever is actually making the best content right now. |
| **No verifiable sources** | You cannot click a hallucinated URL. You cannot audit what data the LLM used to make its ranking decision. |

### What this project does instead

`srp` uses the LLM for tasks where hallucination risk is low:

- **Summarising text it has directly received** — the transcript is handed to the LLM verbatim; it cannot invent content that is not there.
- **Classifying a query** — turning "who is winning the LLM benchmarks race?" into a topic + purpose is a short classification task, not open-ended generation.
- **Writing synthesis prose** — Section 10 and 11 synthesise data the pipeline has already collected and verified; the LLM does not generate facts from memory.

All facts that appear in the report come from the YouTube API (view counts, subscriber counts, publish dates) or from corroboration web searches — not from the LLM's training data.

### Limitations and loopholes of the current approach

No approach is perfect. Here is what can go wrong with `srp`'s method:

**Data quality issues**

- **YouTube's API can return low-quality results.** The search ranking is YouTube's own algorithm, which optimises for watch time, not research quality. The first 20 results may not be the 20 most relevant videos on the topic.
- **Subscriber count is a weak credibility proxy.** A channel can have millions of subscribers but still produce misinformation. The trust score uses it because it is the only persistent credibility signal available without human review.
- **No peer-review signal.** Academic or expert content that does not perform well algorithmically will rank below highly optimised YouTube content, even if it is more credible.

**Transcript reliability**

- **Auto-captions can be wrong.** YouTube's auto-generated captions contain transcription errors, especially for technical jargon, non-native speakers, or fast speech. The LLM summary inherits those errors.
- **Whisper is a fallback, not a guarantee.** If no captions exist and Whisper fails, the pipeline falls back to the video description, which is the least reliable source of content.

**Scoring model limitations**

- **Single-snapshot data.** Scores reflect one point in time. A video that published 24 hours ago with 10 000 views looks worse than a 30-day-old video with 50 000 views, even if its velocity is faster. The trend z-score partially compensates for this, but not fully.
- **Cross-channel repetition is not yet implemented.** The `market_gap` and `z_cross_channel_repetition` components currently default to 0 and 0.0. This means opportunity and trend scores undercount saturation signals.
- **Corroboration is not fact-checking.** Finding 4 web sources that repeat a claim does not mean the claim is true — it may mean misinformation spread widely. The corroboration score measures *prevalence*, not *accuracy*.

**What could be improved**

- **Longitudinal tracking** — running the same query weekly and comparing scores over time would reveal trends that a single snapshot misses (this requires the planned SQLite history store).
- **Semantic deduplication** — the current deduplicator uses fuzzy title matching. Two videos covering the same story but with different titles are counted as separate items.
- **Richer trust signals** — cross-referencing the channel against known-credible-source lists, checking for linked academic affiliations, or verifying channel age would improve trust precision.
- **Configurable weights** — the trust/trend/opportunity weights are currently fixed. A research use case and a content-strategy use case have different priorities; exposing the weights as config would make the tool more flexible.
- **Real cross-channel saturation** — implementing the cross-channel repetition signal (does the same claim appear in multiple videos across this result set?) would make the opportunity and trend scores substantially more meaningful.

---

## See also

- [Statistics](statistics.md) — the 15+ models that run on scored results
- [Charts](charts.md) — visual outputs derived from the scoring data
- [Corroboration](corroboration.md) — how claims are cross-checked
- [LLM Runners](llm-runners.md) — what the LLM is used for and how to configure it
- [Architecture](architecture.md) — system design and data flow
