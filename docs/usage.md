# Usage Guide

[Home](README.md) → Usage

---

## Quickstart

```bash
srp config set-secret YOUTUBE_API_KEY
srp research "AI safety" "latest-news"
```

`srp` prints a Markdown summary to stdout and writes a self-contained HTML report to `~/.social-research-probe/reports/`. Open it in any browser.

---

## Core Concepts

### Topics

A topic is a search subject — e.g. `"AI safety"`, `"climate tech"`. Topics are registered in `~/.social-research-probe/topics.json` and reused across runs.

```bash
srp show-topics
srp update-topics --add "climate tech"
srp update-topics --remove "old-topic"
```

### Purposes

A purpose defines the research intent and shapes how queries are enriched and results are weighted — e.g. `"latest-news"` prioritises recency, `"emerging-research"` prioritises academic credibility.

```bash
srp show-purposes
srp update-purposes --add "emerging-research"="Track peer-reviewed preprints"
```

### Pending proposals

`suggest-topics` and `suggest-purposes` use the configured LLM runner to generate proposals. Proposals land in a pending queue and do not take effect until you explicitly accept them.

```bash
srp suggest-topics
srp show-pending
srp apply-pending          # accept all
srp discard-pending        # reject all
```

---

## Running Research

### Single topic, single purpose

```bash
srp research "AI agents" "latest-news"
```

### Multiple purposes (comma-separated)

```bash
srp research "AI agents" "latest-news,trends"
```

### Explicit platform

```bash
srp research youtube "AI agents" "latest-news"
```

### Natural-language query

When the argument looks like a question or sentence, `srp` auto-classifies it into a topic and purpose using the configured LLM runner. Requires `llm.runner != none`.

```bash
srp research "who is winning the LLM benchmarks race?"
```

### Excluding YouTube Shorts

```bash
srp research "AI agents" "latest-news" --no-shorts
```

---

## Controlling the Number of Videos

**How many videos are fetched** is set by `platforms.youtube.max_items` (default: 20). Increase it to cast a wider net; decrease it to run faster.

```bash
srp config set platforms.youtube.max_items 50   # fetch up to 50 videos
srp config set platforms.youtube.max_items 10   # fetch only 10 for a quick run
```

**How far back to search** is controlled by `platforms.youtube.recency_days` (default: 90 days).

```bash
srp config set platforms.youtube.recency_days 30   # last month only
srp config set platforms.youtube.recency_days 365  # last year
```

**The top-N videos that get fully enriched** (transcripts fetched, LLM summaries generated, corroboration run) is fixed at **5**. These are the highest-scoring items from the fetched pool. Fetching more videos (`max_items`) gives the scoring stage more to rank, which can improve the quality of the top-5 selection.

---

## Reading the Report

After each run, `srp` prints:

```
[srp] HTML report: file:///~/.social-research-probe/reports/<filename>.html
```

The HTML report contains all 11 sections, embedded charts, and a built-in text-to-speech player. Sections 10–11 (Compiled Synthesis and Opportunity Analysis) are written inline when `llm.runner` is configured.

---

## Generating a Report After the Fact

To attach synthesis sections to an existing research packet:

```bash
srp report \
  --packet ~/.social-research-probe/packets/my-packet.json \
  --synthesis-10 /tmp/s10.txt \
  --synthesis-11 /tmp/s11.txt \
  --out ~/Desktop/report.html
```

---

## Corroboration Modes

`srp` auto-corroborates the top-5 results using web-search backends. The mode is set by `corroboration.backend`:

| Mode | Behaviour |
|---|---|
| `host` (default) | Auto-discovers which backends have valid API keys and uses all available ones |
| `exa` / `brave` / `tavily` | Forces a specific backend regardless of other configured keys |
| `llm_cli` | Uses the configured LLM runner to corroborate (no external search API needed) |
| `none` | Disables corroboration entirely |

```bash
srp config set corroboration.backend exa    # force Exa only
srp config set corroboration.backend none   # disable
```

---

## Configuration Reference

```bash
srp config show                                   # print all settings
srp config set llm.runner claude                  # set LLM runner
srp config set platforms.youtube.max_items 50     # fetch up to 50 videos
srp config set platforms.youtube.recency_days 30  # limit to last 30 days
srp config set corroboration.backend host         # auto-discover backends
```

---

## Skill Bundle

After running `srp install-skill`, invoke `srp` from inside a Claude Code session:

```
/srp research "AI safety" "latest-news"
```

The skill shells out to the `srp` CLI and formats the output for chat.

---

## See also

- [Command Reference](commands.md) — full flag listing and exit codes
- [Installation](installation.md) — setup and secret configuration
- [Architecture](architecture.md) — pipeline internals
