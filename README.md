# social-research-probe

**Local-first social-media research CLI and bundled `/srp` operator skill**

[![CI](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml/badge.svg)](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![Python >=3.11](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](https://pypi.org/project/social-research-probe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/reshinto/social-research-probe/blob/main/LICENSE)

`srp` turns a research question into an auditable evidence packet. It fetches platform results, classifies source type, scores sources, enriches the strongest items, extracts and corroborates claims when providers are available, clusters narratives, computes statistics, renders charts, writes reports, exports CSV/Markdown/JSON artifacts, and can persist the run to SQLite.

YouTube is the only concrete source adapter in the current codebase. The CLI also exposes an `all` platform that runs every registered concrete platform; today that means YouTube.

## Quickstart

```bash
srp research youtube "what are researchers saying about model collapse?" "latest-news"
```

If you omit the platform, `srp research` targets `all`:

```bash
srp research "what are researchers saying about model collapse?" "latest-news"
```

Install, configure a YouTube key, and choose optional LLM/corroboration providers with [docs/installation.md](docs/installation.md).

## Pipeline

![Research data flow](docs/diagrams/data-flow.svg)

One YouTube run follows this order:

1. Parse topic and purpose.
2. Fetch YouTube items and engagement metrics.
3. Classify source type: `primary`, `secondary`, `commentary`, or `unknown`.
4. Score and rank by trust, trend, opportunity, and overall score.
5. Run transcripts, statistics, and chart rendering after scoring.
6. Fetch comments, build text surrogates, and summarize top-N items.
7. Extract claims, corroborate them, and cluster narratives.
8. Generate synthesis, assemble the report packet, and attach structured synthesis.
9. Render HTML/Markdown, optional narration, export files, and SQLite persistence.

The design keeps cheap deterministic work first. LLM calls and paid/search-provider work are gated by config and concentrated on top-ranked items.

## Common commands

```bash
srp setup
srp config path
srp config show
srp config set-secret youtube_api_key
srp config set llm.runner gemini
srp config set technologies.gemini true
srp research youtube "AI agents" "latest-news,trends" --no-shorts
srp demo-report
srp db stats
srp claims list --needs-review
srp serve-report --report ~/.social-research-probe/reports/report.html
```

## Documentation

Start with [docs/README.md](docs/README.md). The docs are organized as a curriculum:

| Read | Purpose |
| --- | --- |
| [Objective](docs/objective.md) and [How it works](docs/how-it-works.md) | Understand the product and one end-to-end run. |
| [Installation](docs/installation.md), [Usage](docs/usage.md), and [Commands](docs/commands.md) | Install and operate the CLI. |
| [Configuration](docs/configuration.md), [Data directory](docs/data-directory.md), and [Security](docs/security.md) | Control local state, secrets, providers, and outputs. |
| [Architecture](docs/architecture.md), [Module reference](docs/module-reference.md), and [Design patterns](docs/design-patterns.md) | Learn the codebase boundaries. |
| [Python guide](docs/python-language-guide.md) | Learn enough Python to work in this repository. |
| [Adding a platform](docs/adding-a-platform.md), [Adding a service](docs/adding-a-service.md), and [Adding a technology](docs/adding-a-technology.md) | Extend the system safely. |

## Architecture in one paragraph

The CLI parses commands and dispatches to command modules. Research commands build a `PipelineState` and send it to the platform orchestrator. Platform stages decide order and source-specific behavior. Services coordinate one reusable task and return `ServiceResult` objects. Technologies are atomic adapters or algorithms behind feature flags and cache. Utilities hold shared config, state, cache, display, parsing, report, and persistence helpers.

## License

MIT © 2026 Terence. See [LICENSE](LICENSE).
