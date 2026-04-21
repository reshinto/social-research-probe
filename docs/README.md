# social-research-probe Documentation

[Home](README.md)

`srp` is an evidence-first research CLI that does most of its work on your own computer and calls an LLM only when no cheaper tool will do. You give it a topic and a purpose; it fetches content from a social platform, scores it, runs 20+ statistical models, corroborates the top results against the web, and produces a Markdown + HTML report.

---

## New here? Start with these

| Document | What it covers |
|---|---|
| [Objective & Roadmap](objective.md) | What the project is, who it's for, philosophy, and what's planned |
| [How It Works](how-it-works.md) | Plain-English walkthrough of a `srp research` run |
| [Cost Optimization](cost-optimization.md) | Every place the design avoids an LLM call; recipes by budget |
| [Installation](installation.md) | Step-by-step setup: install, API keys, LLM runner, verification |
| [Usage Guide](usage.md) | Run your first research, read the output, Claude Code skill flow |
| [Corroboration](corroboration.md) | What claim corroboration is and how to configure it |

---

## Reference

| Document | What it covers |
|---|---|
| [Configuration](configuration.md) | Every config key, env overrides, config/secrets lifecycle |
| [LLM Runners](llm-runners.md) | Runner comparison, Gemini CLI browser auth, ensemble mode |
| [Command Reference](commands.md) | Every `srp` subcommand, flag, exit code, environment variable |
| [Statistics](statistics.md) | All 20+ statistical models: what they measure and how to interpret |
| [Charts](charts.md) | Every chart: what it shows, how to read it, what to look for |
| [Statistical Model Reference](model-applicability.md) | Model-to-module mapping, minimum dataset sizes |
| [Synthesis Authoring](synthesis-authoring.md) | Override sections 10–11 in the HTML report with custom text |

---

## For contributors

| Document | What it covers |
|---|---|
| [Architecture](architecture.md) | System design, data flow, async model, extension points |
| [Module Reference](module-reference.md) | Every root file and folder: what it is and why it exists |
| [Adding a Platform](adding-a-platform.md) | Walkthrough for adding a new content source (TikTok, Reddit, RSS, …) |
| [Design Patterns](design-patterns.md) | Adapter, registry, strategy, pipeline — with code examples |
| [Python Language Guide](python-language-guide.md) | All 13 Python idioms used in the codebase |
| [Testing](testing.md) | Test tiers, TDD workflow, 100% coverage gate, fake adapters |
| [Security](security.md) | Secret storage, trust boundaries, hardening checklist |

---

## Project files

| File | What it covers |
|---|---|
| [CHANGELOG.md](../CHANGELOG.md) | Release history |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Development workflow, TDD rules, file-size limits |
| [SECURITY.md](../SECURITY.md) | Responsible disclosure policy |
| [LICENSE](../LICENSE) | MIT license |
