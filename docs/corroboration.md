# Corroboration

[Home](README.md) → Corroboration

Corroboration is the process of cross-checking the claims made in YouTube videos against independent external sources. This page explains what it is, why it matters, how the pipeline implements it, and how to configure it.

---

## What is corroboration?

When a YouTube video makes a claim — "AI safety researchers at DeepMind published a new paper" — that claim is self-reported. The video creator has no independent verification. Corroboration asks: **does any other source on the web support or contradict this claim?**

`srp` automatically extracts the key claims from each of the top-5 scored videos and queries one or more web-search APIs (Exa, Brave Search, or Tavily) to find supporting or contradicting evidence. The results appear in **Section 6 (Evidence)** of your report.

---

## Why it matters

Without corroboration, your research report is a curated list of YouTube opinions. With corroboration, each top-5 item is annotated with:

- Whether independent sources confirm the claim
- Links to those sources (news articles, academic papers, other web content)
- A credibility signal that no amount of in-platform scoring can provide

This is especially important for topics where misinformation spreads easily (health, finance, politics) or where a single influential creator can dominate search results without being authoritative.

---

## How it works

For each of the top-5 scored videos, the pipeline:

1. **Extracts claims** — from the LLM-generated transcript summary, the video title, and channel metadata.
2. **Queries backends** — sends each claim to the configured corroboration backend(s) as a web search query.
3. **Collects evidence** — each backend returns a list of snippets from external sources (title, URL, excerpt).
4. **Attaches results** — evidence snippets are stored in the packet and rendered in Section 6.

Corroboration runs concurrently across all available backends using `asyncio.gather`, so having multiple API keys does not increase run time.

The maximum number of claims checked per item is controlled by `corroboration.max_claims_per_item` (default: 5). The total budget per run is `corroboration.max_claims_per_session` (default: 15). Adjust these if you want broader or narrower coverage:

```bash
srp config set corroboration.max_claims_per_item 3    # fewer queries per video
srp config set corroboration.max_claims_per_session 30 # more total claims
```

---

## Backends

### Exa

**What it is:** A neural search engine optimised for semantic similarity. Finds web pages that are conceptually related to the claim, not just keyword matches.

**Best for:** Research topics, academic claims, nuanced concepts where exact keywords may not appear in relevant sources.

**API key:** [exa.ai](https://exa.ai) — free tier available.

```bash
srp config set-secret EXA_API_KEY
```

### Brave Search

**What it is:** A privacy-focused general web search engine with an independent index (not derived from Google or Bing).

**Best for:** Current events, news, fast-moving topics. Good coverage of recent web pages.

**API key:** [api.search.brave.com](https://api.search.brave.com) — free tier available.

```bash
srp config set-secret BRAVE_API_KEY
```

### Tavily

**What it is:** A search API designed specifically for AI agents, returning clean structured snippets rather than raw HTML.

**Best for:** General use. Returns reliable, well-formatted excerpts that are easy for the LLM synthesis layer to use.

**API key:** [tavily.com](https://tavily.com) — free tier available.

```bash
srp config set-secret TAVILY_API_KEY
```

### LLM CLI (`llm_cli`)

Uses the configured LLM runner to generate corroboration evidence from its training data rather than querying a live search API. No external search key is required.

**Best for:** Air-gapped environments or when you do not want to register for search APIs. Less reliable than live web search for recent events.

```bash
srp config set corroboration.backend llm_cli
```

---

## Configuration

### Mode selection

```bash
srp config set corroboration.backend host       # auto-discover all configured backends (default)
srp config set corroboration.backend exa        # force Exa only
srp config set corroboration.backend brave      # force Brave only
srp config set corroboration.backend tavily     # force Tavily only
srp config set corroboration.backend llm_cli    # use LLM runner (no search API needed)
srp config set corroboration.backend none       # disable corroboration entirely
```

### Auto-discovery (`host` mode)

When `backend = host`, the pipeline calls `health_check()` on each backend at the start of the run. Any backend whose API key is configured and whose health check passes is used. This means you can add keys over time and they are automatically picked up without changing the config.

### Checking which backends are available

```bash
srp config check-secrets --corroboration exa
srp config check-secrets --corroboration brave
srp config check-secrets --corroboration tavily
```

Each prints a JSON object with `present` and `missing` keys.

---

## When corroboration is skipped

Corroboration is skipped (and a warning added to Section 9) when:

- `corroboration.backend = none`
- No corroboration API keys are configured and `llm.runner = none`
- All configured backends fail their `health_check()` at runtime

When skipped, Section 6 (Evidence) of the report shows `_(corroboration skipped)_`. The rest of the report is unaffected.

---

## Interpreting Section 6 (Evidence)

Section 6 shows a summary for each top-5 item. For each item you will see:

- **Supported** — the number of independent sources that confirm or are consistent with the video's claims
- **Contradicted** — sources that directly disagree
- **Snippets** — short excerpts from the most relevant sources, with URLs

A high supported count does not mean the video is correct — it means the claim is *common* on the web, which could mean it is widely accepted or widely repeated misinformation. Always follow the source links and read them in context.

---

## See also

- [Installation](installation.md) — how to get and store API keys
- [Usage Guide](usage.md) — corroboration mode config commands
- [Security](security.md) — which domains are contacted and how keys are stored
