# social-research-probe

**Evidence-first social-media research CLI + Claude Code skill**

[![CI](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml/badge.svg)](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![Python >=3.11](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](https://pypi.org/project/social-research-probe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/reshinto/social-research-probe/blob/main/LICENSE)

`srp` is a local-first research CLI for turning platform search results into a structured evidence packet. YouTube is the first implemented platform, but the design is meant to grow toward TikTok, Instagram, X, web search, RSS, forums, and other public sources. A run fetches candidate items, ranks them by trust/trend/opportunity, enriches the strongest items, corroborates claims when providers are configured, runs statistics, renders charts, and writes Markdown/HTML reports.

## Quickstart

```bash
srp research "what are researchers saying about model collapse?" "latest-news"
```

This command uses the default platform, currently YouTube, and the saved purpose named `latest-news`. A purpose tells the system what kind of research lens to apply. For example, a breaking-news purpose should value freshness and corroboration, while an evergreen-analysis purpose might value source quality and transcript depth more heavily.

For installation steps, API keys, and runner setup, use [docs/installation.md](docs/installation.md). That file is the setup reference.

## What happens during research

![Research data flow](docs/diagrams/data-flow.svg)

1. Parse the topic and purpose.
2. Fetch platform items and engagement metrics.
3. Rank items with trust, trend, opportunity, and overall score.
4. Run transcript fetching, statistics, and charts.
5. Summarize top-N items when an LLM runner is enabled.
6. Corroborate claims through healthy configured providers.
7. Assemble and render the final report.

## Why it exists

Raw platform search results are hard to audit. A normal research workflow often leaves important decisions hidden: why one source was chosen, which claims were checked, whether summaries came from transcripts or guesses, and how much of the process depended on paid providers. This project turns a research question into a repeatable evidence packet: source items, scores, transcripts, summaries, corroboration evidence, statistical highlights, charts, and a report.

The design keeps cheap local work first. Search, scoring, caching, statistics, and charting can happen before any LLM or paid search provider is used. Expensive work is gated behind configuration and focused on the top-ranked items, so users can understand and control the cost of a run.

## Common commands

```bash
srp research "AI agents" "latest-news"
srp research youtube "AI agents" "latest-news,trends" --no-shorts
srp config show
srp config set llm.runner gemini
srp config set platforms.youtube.enrich_top_n 3
srp config set-secret youtube_api_key
srp serve-report --report ~/.social-research-probe/reports/report.html
```

## Documentation

Start with [docs/README.md](docs/README.md). Key pages:

| Page | Purpose |
| --- | --- |
| [Objective](docs/objective.md) | Why this project exists. |
| [How it works](docs/how-it-works.md) | Plain-English pipeline walkthrough. |
| [Architecture](docs/architecture.md) | System design, diagrams, and tradeoffs. |
| [Design patterns](docs/design-patterns.md) | Patterns used in the codebase with examples. |
| [Usage](docs/usage.md) | Day-to-day CLI workflows. |
| [Configuration](docs/configuration.md) | Config, secrets, gates, and data directory behavior. |
| [API costs and keys](docs/api-costs-and-keys.md) | Which features are free, quota-based, paid, or authenticated through external CLIs. |
| [Commands](docs/commands.md) | Full command surface, including Claude Code `/srp` forms. |
| [Root files](docs/root-files.md) | Purpose of every repository root file and support directory. |
| [Scoring](docs/scoring.md) | How trust, trend, opportunity, and overall ranking are calculated. |
| [Python guide](docs/python-language-guide.md) | Python concepts used in the repository. |

## Architecture in one paragraph

The CLI dispatches commands into a platform orchestrator. A platform adapter owns source-specific fetching and stage order; today that adapter is YouTube. Services coordinate reusable tasks such as scoring, enrichment, statistics, synthesis, and reporting. Technologies are atomic adapters or pure algorithms, such as a transcript fetcher, chart renderer, LLM runner, or search provider. Shared utilities handle config, cache, local state, validation, display, and subprocess calls.

See [docs/architecture.md](docs/architecture.md) for the full system design.

## License

MIT © 2026 Terence — see [LICENSE](LICENSE).
