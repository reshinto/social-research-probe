# social-research-probe

**Evidence-first social-media research CLI + Claude Code skill**

[![CI](https://github.com/user/social-research-probe/actions/workflows/ci.yml/badge.svg)](https://github.com/user/social-research-probe/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![Python versions](https://img.shields.io/pypi/pyversions/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`srp` fetches YouTube content, scores it by trust/trend/opportunity, runs a
statistical analysis suite, auto-corroborates claims, generates LLM synthesis
sections, and renders an HTML report — all from a single CLI command.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Quickstart](#quickstart)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Documentation map](#documentation-map)
6. [Architecture](#architecture)
7. [Contributing](#contributing)
8. [Security](#security)
9. [License](#license)
10. [Changelog](#changelog)

---

## What it does

`srp research` runs a five-stage evidence pipeline:

1. **Fetch** — queries YouTube (or other adapters) for recent content on a topic,
   applying purpose-driven search enrichment.
2. **Score** — ranks items by a composite trust / trend / opportunity score
   derived from channel credibility, view velocity, and cross-channel repetition.
3. **Enrich** — fetches transcripts (yt-dlp captions → Whisper fallback) and
   generates 100-word+ LLM summaries via a Claude + Gemini + Codex ensemble.
4. **Analyse** — runs 15+ statistical models (regression, Bayesian linear,
   bootstrap, k-means, PCA, Kaplan-Meier, …) and renders charts as PNGs.
5. **Synthesise** — auto-corroborates top-5 claims via Exa/Brave/Tavily, attaches
   structured LLM synthesis sections, and emits a Markdown + HTML report.

It also ships as a **Claude Code skill** (`/srp`) so you can invoke research,
manage topics/purposes, and receive formatted reports directly inside a Claude
Code session.

---

## Quickstart

```bash
pip install social-research-probe
srp research "AI safety" "latest-news"
```

Or in natural-language mode:

```bash
srp research "what are researchers saying about model collapse?"
```

---

## Installation

```bash
# From PyPI
pip install social-research-probe

# From source (development)
git clone https://github.com/user/social-research-probe
cd social-research-probe
pip install -e '.[dev]'
```

Required environment variables (copy `.env.example` and fill in):

```
YOUTUBE_API_KEY=...
EXA_API_KEY=...          # optional — corroboration
BRAVE_API_KEY=...        # optional — corroboration
TAVILY_API_KEY=...       # optional — corroboration
```

Secrets are stored securely via `srp config set-secret <name>`.

---

## Usage

```bash
# Research a topic with a specific purpose
srp research "AI agents" "latest-news"
srp research youtube "AI agents" "latest-news,trends"

# Natural-language query (auto-classifies topic + purpose)
srp research "who is winning the LLM benchmarks race?"

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

---

## Documentation map

| Document | Description |
|---|---|
| [docs/MODEL_APPLICABILITY.md](docs/MODEL_APPLICABILITY.md) | Which LLM models are recommended for which pipeline stages |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow, TDD rules, file size limits, versioning |
| [SECURITY.md](SECURITY.md) | Responsible disclosure policy and scope |
| [CHANGELOG.md](CHANGELOG.md) | Release history in Keep-a-Changelog format |

---

## Architecture

`srp` is a Python CLI (`social_research_probe/cli/`) that delegates to a
research pipeline (`social_research_probe/pipeline/`). The pipeline calls
platform adapters, a scoring layer, a stats suite, an LLM ensemble, and
corroboration backends, then feeds the result to the synthesis layer which
produces Markdown + HTML output.

Key packages:

| Package | Responsibility |
|---|---|
| `cli/` | Argument parsing, subcommand dispatch, synthesis attachment |
| `pipeline/` | Orchestration: fetch → score → enrich → stats → corroborate |
| `platforms/` | Platform adapters (YouTube today; extensible) |
| `synthesize/` | Packet formatting, statistical explanations, LLM contracts |
| `corroboration/` | Exa / Brave / Tavily backends + claim host |
| `llm/` | Multi-LLM ensemble, runner registry, async subprocess execution |
| `stats/` | 15+ statistical models (regression, clustering, survival, …) |
| `viz/` | PNG chart rendering via matplotlib |

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
