# social-research-probe

**Evidence-first social-media research CLI + Claude Code skill**

[![CI](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml/badge.svg)](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![Python >=3.11](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](https://pypi.org/project/social-research-probe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/reshinto/social-research-probe/blob/main/LICENSE)

`srp` fetches YouTube content, scores it by trust/trend/opportunity, auto-corroborates claims, runs 20+ statistical models, and renders an HTML report — all from a single CLI command.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Why this exists](#why-this-exists)
3. [Quickstart](#quickstart)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Configuration](#configuration)
7. [Roadmap — what's planned](#roadmap)
8. [Documentation](#documentation)
9. [Architecture](#architecture)
10. [Contributing](#contributing)
11. [Security](#security)
12. [License](#license)
13. [Changelog](#changelog)

---

## What it does

`srp research` runs a five-stage evidence pipeline:

1. **Fetch** — queries YouTube for recent content on a topic (configurable count and recency window).
2. **Score** — ranks items by a composite trust / trend / opportunity score derived from channel credibility, view velocity, and cross-channel repetition.
3. **Enrich** — fetches transcripts (yt-dlp captions → Whisper fallback) and generates 100-word LLM summaries for the top results.
4. **Analyse** — runs 20+ statistical models (regression, Bayesian linear, bootstrap, k-means, PCA, Kaplan–Meier, …) and renders charts as PNGs.
5. **Synthesise** — auto-corroborates the top results via Exa/Brave/Tavily, attaches structured LLM synthesis sections, and emits a Markdown + HTML report.

It also ships as a **Claude Code skill** (`/srp`) so you can invoke research, manage topics/purposes, and receive formatted reports directly inside a Claude Code session.

---

## Why this exists

`srp` is an **evidence-first research CLI**. It does most of the work on your own computer and only calls an LLM when no cheaper tool can do the job.

- **Objective** — conduct real research with citations, the lowest possible cost per query, and no lock-in to any single model.
- **Audience** — independent researchers, journalists, content strategists, analysts, and indie builders who need repeatable research without burning LLM credits.
- **Philosophy** — scoring, stats, charts, transcripts (via captions or local Whisper), and caching all run on your CPU. The LLM is used only for 100-word per-item summaries and the final synthesis sections, behind a swappable runner interface. If your preferred model disappears, change one config key and keep going.
- **Status** — **work in progress (pre-1.0)**. The pipeline, scoring model, and CLI shape are stable. The research-packet schema and additional platforms/backends are still evolving. Pin a version in production.

See [docs/objective.md](docs/objective.md) for the full rationale and [docs/cost-optimization.md](docs/cost-optimization.md) for every place the design avoids an LLM call.

---

## Quickstart

```bash
pip install social-research-probe
srp config set-secret youtube_api_key
srp research "AI safety" "latest-news"
```

Or in natural-language mode from the CLI (requires `llm.runner` configured):

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
srp config set-secret youtube_api_key
```

### Pick an LLM runner — Gemini CLI is the free default

`srp` does not bundle any LLM. It shells out to the runner's CLI — so **you must install the matching CLI on your machine yourself** (via npm, brew, a package manager, or an Ollama install for the local runner) and authenticate it before pointing `srp` at it.

`srp` can use Claude, Gemini, Codex, or a local model. **Gemini CLI is recommended as the default for cost-conscious users**: it logs in via a browser OAuth flow, needs no API key, and runs on a free tier for typical workloads. Install the [Gemini CLI](https://github.com/google-gemini/gemini-cli) and log in, then:

```bash
srp config set llm.runner gemini
```

The `llm_search` corroboration backend is now runner-agnostic: it dispatches via your configured `llm_runner`, so Claude's `web_search` tool and Codex's `--search` flag work the same way as Gemini's grounded search. See [docs/llm-runners.md](docs/llm-runners.md) for the capability matrix and [docs/corroboration.md](docs/corroboration.md) for the full flow.

See [docs/installation.md](docs/installation.md) for full setup including optional keys and the Claude Code skill bundle.

---

## Usage

```bash
# Research a topic with a specific purpose
srp research "AI agents" "latest-news"
srp research youtube "AI agents" "latest-news,trends"

# Natural-language query (auto-classifies topic + purpose)
srp research "who is winning the LLM benchmarks race?"

# Manage topics and purposes
srp show-topics
srp update-topics --add '"climate tech"'
srp update-purposes --add '"emerging-research"="Track peer-reviewed preprints"'

# Config
srp config set llm.runner claude
srp config set-secret youtube_api_key
```

Full flag reference: `srp --help` / `srp <subcommand> --help`.

### Claude Code skill

```text
srp install-skill

/srp research "AI safety" "latest-news"
/srp show-topics
/srp show-purposes
/srp suggest-topics --count 3
/srp show-pending
/srp apply-pending --topics all --purposes all
```

The Claude Code skill shells out to the same `srp` CLI, so the flags and quoted edit syntax are identical. For example: `/srp update-topics --add '"climate tech"'`. When `llm.runner = none`, the skill can still use the host model for natural-language request mapping and inline narrative sections; when a concrete runner is configured, the skill defers to the CLI-produced LLM output.

See [docs/usage.md](docs/usage.md) for a complete guide including Claude Code workflows, corroboration modes, report generation, and the pending-proposal review flow.

---

## Configuration

Key settings in `~/.social-research-probe/config.toml`:

| Setting                          | Default | What it controls                             |
| -------------------------------- | ------- | -------------------------------------------- |
| `platforms.youtube.max_items`    | `20`    | How many videos to fetch per search          |
| `platforms.youtube.enrich_top_n` | `5`     | How many top items get transcripts + summaries (biggest cost lever) |
| `llm.runner`                     | `none`  | Which LLM runner to use — `gemini` is the free default |
| `corroboration.backend`          | `host`  | `host` tries every healthy backend; `none` disables corroboration |

Change any setting with `srp config set <key> <value>`. Running `srp setup` again after an upgrade **adds missing keys without overwriting** your edits, and `secrets.toml` is never overwritten (it's chmod `0600`).

See [docs/configuration.md](docs/configuration.md) for the full key list, env overrides, and ready-made recipes (cheapest / deepest / fastest / offline).

---

## Roadmap

Today: **YouTube**, 4 LLM runners (`claude`, `gemini`, `codex`, `local`), 4 corroboration backends (`llm_search`, `tavily`, `brave`, `exa`).

Planned platforms — each implemented by adding one adapter to [social_research_probe/platforms/](social_research_probe/platforms/):

- **TikTok**, **X / Twitter**, **Facebook**, **Reddit** — social adapters.
- **RSS**, **web search**, **web crawling** — long-tail and general-web sources.
- **Document research** — PDF, arXiv, Google Drive, and local files.

None of these require new LLM capabilities. See [docs/objective.md](docs/objective.md#roadmap) for motivation and [docs/adding-a-platform.md](docs/adding-a-platform.md) for the contract.

---

## Documentation

| Document                                               | What it covers                                                    |
| ------------------------------------------------------ | ----------------------------------------------------------------- |
| [docs/README.md](docs/README.md)                       | Documentation hub — all docs grouped by audience                  |
| [docs/objective.md](docs/objective.md)                 | Project objective, audience, philosophy, roadmap                  |
| [docs/how-it-works.md](docs/how-it-works.md)           | What happens during a `srp research` run, in plain English        |
| [docs/cost-optimization.md](docs/cost-optimization.md) | Every place the design avoids an LLM call; recipes by budget      |
| [docs/installation.md](docs/installation.md)           | Install (pip/pipx/uvx), API keys, LLM runner, verification        |
| [docs/usage.md](docs/usage.md)                         | Run research, read output, Claude Code skill workflow             |
| [docs/configuration.md](docs/configuration.md)         | Every config key, env overrides, config/secrets lifecycle         |
| [docs/corroboration.md](docs/corroboration.md)         | Claim corroboration: backends, free tiers, configuration          |
| [docs/llm-runners.md](docs/llm-runners.md)             | Runner comparison, auth, ensemble mode, runner-agnostic agentic search |
| [docs/data-directory.md](docs/data-directory.md)       | Canonical reference for every artefact under `~/.social-research-probe/` |
| [docs/llm-reliability-harness.md](docs/llm-reliability-harness.md) | Multi-sample judge-LLM reliability harness with variance gates |
| [docs/runtime-dependencies.md](docs/runtime-dependencies.md) | Every third-party library `srp` imports at runtime — where/why |
| [docs/summary-quality-report.md](docs/summary-quality-report.md) | Diagnosis + Phase 9 redesign of the transcript summarizer       |
| [docs/statistics.md](docs/statistics.md)               | All 20+ statistical models: what they measure, how to interpret   |
| [docs/charts.md](docs/charts.md)                       | Every chart: what it shows, where it's saved                      |
| [docs/commands.md](docs/commands.md)                   | Every `srp` subcommand, flag, exit code, environment variable     |
| [docs/synthesis-authoring.md](docs/synthesis-authoring.md) | Override sections 10–11 in the HTML report                    |
| [docs/architecture.md](docs/architecture.md)           | System design, data flow, tradeoffs, extension points             |
| [docs/module-reference.md](docs/module-reference.md)   | Every root file and folder: what it is and why it exists          |
| [docs/adding-a-platform.md](docs/adding-a-platform.md) | How to add a new platform adapter (TikTok, Reddit, RSS, …)        |
| [docs/design-patterns.md](docs/design-patterns.md)     | Patterns with code examples and why/why-not rationale             |
| [docs/python-language-guide.md](docs/python-language-guide.md) | All 13 Python idioms used in the codebase                  |
| [docs/testing.md](docs/testing.md)                     | Test tiers, `make test-evidence`, eval scripts, TDD workflow, 100% coverage gate |
| [docs/security.md](docs/security.md)                   | Secret storage, trust boundaries, hardening                       |
| [CONTRIBUTING.md](CONTRIBUTING.md)                     | Development workflow, TDD rules, file-size limits                 |
| [SECURITY.md](SECURITY.md)                             | Responsible disclosure policy                                     |
| [CHANGELOG.md](CHANGELOG.md)                           | Release history                                                   |

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
