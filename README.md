# social-research-probe

**Evidence-first social-media research CLI + Claude Code skill**

[![CI](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml/badge.svg)](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![Python versions](https://img.shields.io/pypi/pyversions/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`srp` fetches YouTube content, scores it by trust/trend/opportunity, auto-corroborates claims, runs 15+ statistical models, and renders an HTML report — all from a single CLI command.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Quickstart](#quickstart)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [Documentation](#documentation)
7. [Architecture](#architecture)
8. [Contributing](#contributing)
9. [Security](#security)
10. [License](#license)
11. [Changelog](#changelog)

---

## What it does

`srp research` runs a five-stage evidence pipeline:

1. **Fetch** — queries YouTube for recent content on a topic (configurable count and recency window).
2. **Score** — ranks items by a composite trust / trend / opportunity score derived from channel credibility, view velocity, and cross-channel repetition.
3. **Enrich** — fetches transcripts (yt-dlp captions → Whisper fallback) and generates 100-word LLM summaries for the top results.
4. **Analyse** — runs 15+ statistical models (regression, Bayesian linear, bootstrap, k-means, PCA, Kaplan–Meier, …) and renders charts as PNGs.
5. **Synthesise** — auto-corroborates the top results via Exa/Brave/Tavily, attaches structured LLM synthesis sections, and emits a Markdown + HTML report.

It also ships as a **Claude Code skill** (`/srp`) so you can invoke research, manage topics/purposes, and receive formatted reports directly inside a Claude Code session.

---

## Quickstart

```bash
pip install social-research-probe
srp config set-secret YOUTUBE_API_KEY
srp research "AI safety" "latest-news"
```

Or in natural-language mode (requires `llm.runner` configured):

```bash
srp research "what are researchers saying about model collapse?"
```

---

## Installation

```bash
# pip
pip install social-research-probe

# pipx (isolated environment, recommended for CLI tools)
pipx install social-research-probe

# uvx (run without installing)
uvx social-research-probe research "AI safety" "latest-news"

# From source (development)
git clone https://github.com/reshinto/social-research-probe
cd social-research-probe
pip install -e '.[dev]'
```

After installing, set your YouTube API key:

```bash
srp config set-secret YOUTUBE_API_KEY
```

See [docs/installation.md](docs/installation.md) for full setup including optional keys and the Claude Code skill bundle.

---

## Usage

```bash
# Research a topic with a specific purpose
srp research "AI agents" "latest-news"
srp research youtube "AI agents" "latest-news,trends"

# Natural-language query (auto-classifies topic + purpose)
srp research "who is winning the LLM benchmarks race?"

# Change how many videos are fetched (default: 20)
srp config set platforms.youtube.max_items 50

# Manage topics and purposes
srp update-topics --add "climate tech"
srp update-purposes --add "emerging-research"="Track peer-reviewed preprints"

# Config
srp config show
srp config set llm.runner claude
srp config set-secret YOUTUBE_API_KEY

# Install as a Claude Code skill
srp install-skill
```

Full flag reference: `srp --help` / `srp <subcommand> --help`.

See [docs/usage.md](docs/usage.md) for a complete guide including corroboration modes, report generation, and the pending-proposal workflow.

---

## Configuration

Key settings in `~/.social-research-probe/config.toml`:

| Setting | Default | What it controls |
|---|---|---|
| `platforms.youtube.max_items` | `20` | How many videos to fetch per search |
| `platforms.youtube.recency_days` | `90` | How far back to search (days) |
| `llm.runner` | `none` | Which LLM to use for summaries and synthesis |
| `corroboration.backend` | `host` | Which web-search backend to corroborate with |

Change any setting with `srp config set <key> <value>`, e.g.:

```bash
srp config set platforms.youtube.max_items 50
srp config set platforms.youtube.recency_days 30
srp config set llm.runner claude
```

---

## Documentation

| Document | What it covers |
|---|---|
| [docs/README.md](docs/README.md) | Documentation hub — all docs by audience |
| [docs/how-it-works.md](docs/how-it-works.md) | How fetching, scoring, and transcripts work; vs pure-LLM approach |
| [docs/installation.md](docs/installation.md) | Install (pip/pipx/uvx), API keys, LLM runner, verification |
| [docs/usage.md](docs/usage.md) | Run research, read output, configure video count |
| [docs/corroboration.md](docs/corroboration.md) | Claim corroboration: what it is, backends, configuration |
| [docs/llm-runners.md](docs/llm-runners.md) | Supported runners, ensemble, what breaks without one |
| [docs/statistics.md](docs/statistics.md) | All 15+ statistical models: what they measure, how to interpret |
| [docs/charts.md](docs/charts.md) | Every chart: what it shows, where it's saved, file persistence |
| [docs/commands.md](docs/commands.md) | Every flag, config key, exit code, environment variable |
| [docs/architecture.md](docs/architecture.md) | System design, data flow, tradeoffs, known limitations |
| [docs/adding-a-platform.md](docs/adding-a-platform.md) | How to add a new platform adapter (TikTok, Reddit, RSS) |
| [docs/design-patterns.md](docs/design-patterns.md) | Patterns with why/why-not rationale |
| [docs/testing.md](docs/testing.md) | Test tiers, TDD workflow, 100% coverage gate |
| [docs/security.md](docs/security.md) | Secret storage, network egress, hardening |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow, TDD rules, file-size limits |
| [SECURITY.md](SECURITY.md) | Responsible disclosure policy |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

---

## Architecture

`srp` is a layered Python CLI. The CLI parses arguments and delegates to the research pipeline, which calls platform adapters, a scoring layer, a stats suite, an LLM ensemble, and corroboration backends, then feeds the result to the synthesis layer.

See [docs/architecture.md](docs/architecture.md) for the full system design including data flow diagrams, async model, design tradeoffs, and extension points.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Security

See [SECURITY.md](SECURITY.md).

---

## License

MIT © 2026 Terence — see [LICENSE](LICENSE).

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
