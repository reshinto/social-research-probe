# Objective & Roadmap

[Home](README.md) → Objective

## What this project is

`srp` is an **evidence-first research CLI** that does most of its work on your own computer and only reaches for an LLM when no cheaper tool will do the job. You give it a topic and a purpose; it fetches real content from a social platform, scores it with transparent formulas, runs 20+ statistical models on it, cross-checks the top results against other sources, and hands you a Markdown + HTML report.

It is **not** a chatbot wrapper. It is not "ask GPT about YouTube" — it actually fetches the data, runs the maths, and cites its sources.

## Target audience

`srp` is for people who need to do real research without burning through LLM credits or trusting a single model's hallucinations:

- **Independent researchers & journalists** — trace what's actually being said on a topic, with citations.
- **Content strategists & creators** — find gaps, timing, and positioning backed by numbers, not vibes.
- **Analysts & consultants** — produce a report you can hand to a client, with every figure traceable.
- **Indie builders** — run hundreds of queries without watching a meter tick.

If you want a quick answer and you're happy to trust a single model, use a chat interface. `srp` is worth the extra setup when you need the research to be **repeatable, auditable, and cheap at scale**.

## Design philosophy — local compute first

Every stage of the pipeline prefers the cheaper path:

| Stage | Where it runs | LLM tokens spent |
|---|---|---|
| Fetch (API call) | your machine → YouTube API | 0 |
| Score (trust / trend / opportunity) | your CPU | 0 |
| Enrich — transcript fetch | captions first, Whisper locally as fallback | 0 |
| Enrich — 100-word summary | LLM on top-N only (default 5) | bounded |
| Stats (20+ models) | your CPU (scipy + Python stdlib) | 0 |
| Charts (10 types) | your CPU (matplotlib) | 0 |
| Corroboration | web-search API (Gemini / Tavily / Brave / Exa) | bounded |
| Report synthesis | LLM on one summary prompt | bounded |

Translation: an average run spends **tens of kilobytes** of LLM context, not megabytes. If the runner is unavailable, the report still renders — Compiled Synthesis, Opportunity Analysis, and Final Summary are the only fields that become placeholders, while per-item summaries fall back to transcript or description excerpts.

Because the LLM is behind a swappable runner interface (`llm/registry.py`), the project is not tied to any one model provider. If your preferred LLM becomes expensive, slow, or discontinued, you change `llm.runner` in `config.toml` and keep going.

## Status — work in progress

`srp` is **pre-1.0**. What this means concretely:

- **Stable:** the 5-stage pipeline, scoring model, statistical suite, caching layer, and CLI command shape.
- **Changing:** the research-packet JSON schema, new config keys, additional platforms, additional corroboration backends.
- **Experimental:** the natural-language research mode, the LLM ensemble, the synthesis section templates.

Breaking changes may ship until v1.0. Pin a version in production.

## Roadmap

![Supported today vs planned platforms/backends](diagrams/roadmap.svg)

Today `srp` supports **one platform (YouTube), four LLM runners (claude, gemini, codex, local), and four corroboration backends (llm_search, tavily, brave, exa)**. The extension points ([platforms/base.py](../social_research_probe/platforms/base.py), [llm/registry.py](../social_research_probe/services/llm/registry.py), [corroboration/registry.py](../social_research_probe/services/corroborating/registry.py)) are designed so adding any of the below is a matter of implementing one interface and registering it.

Planned platforms:

- **TikTok** — video search, captions, author metadata.
- **X / Twitter** — tweet search, thread reconstruction, engagement signals.
- **Facebook** — public page posts.
- **Reddit** — subreddit and search APIs, comment-tree enrichment.
- **RSS feeds** — long-tail blogs and small news outlets.
- **Web search** — a first-class search-engine platform (complementing the corroboration-only usage today).
- **Web crawling** — depth-limited crawl of a seed URL or sitemap for topical coverage.
- **Document research** — local files, PDFs, arXiv, Google Drive, and other knowledge sources.

Planned features:

- Per-platform trust calibration (channels vs accounts vs domains).
- A long-running watch mode that re-runs a query on a schedule.
- A unified cross-platform report (one topic, many sources).

None of this requires new LLM capabilities. All of it is implementable with tools and APIs that exist today.

## What this project is NOT

- It is **not** real-time. Data freshness is bounded by the source API's indexing lag.
- It is **not** a crawler for the whole web — corroboration uses search APIs, not bulk scraping.
- It is **not** a replacement for primary-source research. The report is a starting point, not the final word.
- It is **not** trying to win on raw LLM capability. It wins on **cost, repeatability, and auditability**.

## See also

- [How It Works](how-it-works.md) — what happens during a `srp research` run, in plain English
- [Cost Optimization](cost-optimization.md) — every place the design avoids an LLM call
- [Architecture](architecture.md) — the full system design and extension points
- [Adding a Platform](adding-a-platform.md) — the contract for shipping a new data source
