# social-research-probe Documentation

[Home](README.md)

`srp` is an evidence-first social-media research CLI. You give it a topic and an intent; it fetches YouTube content, scores it, enriches the top results with transcripts and LLM summaries, cross-checks claims with web-search APIs, runs statistical analysis, and produces an HTML report.

---

## New here? Start with these

| Document | What it covers |
|---|---|
| [Installation](installation.md) | Step-by-step setup: install, API keys, LLM runner, verification |
| [Usage Guide](usage.md) | Run your first research, read the output, configure video count |
| [Corroboration](corroboration.md) | What claim corroboration is and how to configure it |

---

## Reference

| Document | What it covers |
|---|---|
| [LLM Runners](llm-runners.md) | Supported LLM runners, configuration, what breaks without one |
| [Command Reference](commands.md) | Every flag, config key, exit code, and environment variable |
| [Statistics](statistics.md) | All 15+ statistical models: what they measure and how to interpret output |
| [Charts](charts.md) | Every chart: what it shows, how to read it, what to look for |
| [Statistical Model Reference](model-applicability.md) | Model-to-module mapping, minimum dataset sizes, planned additions |

---

## For contributors

| Document | What it covers |
|---|---|
| [Architecture](architecture.md) | System design, data flow, async model, design tradeoffs, known limitations |
| [Design Patterns](design-patterns.md) | Adapter, registry, strategy, pipeline, and other patterns — with why/why-not rationale |
| [Python Language Guide](python-language-guide.md) | TypedDicts, protocols, async/await, asyncio.gather, type hints, pytest fixtures |
| [Python Language Guide — Part 2](python-language-guide-2.md) | f-strings, list comprehensions, context managers, dataclasses, import order, `__init__.py` |
| [Testing](testing.md) | Test tiers, TDD workflow, 100% coverage gate, fake adapters |
| [Security](security.md) | Secret storage, network egress, trust boundaries, hardening checklist |

---

## Project files

| File | What it covers |
|---|---|
| [CHANGELOG.md](../CHANGELOG.md) | Release history |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Development workflow, TDD rules, file-size limits |
| [SECURITY.md](../SECURITY.md) | Responsible disclosure policy |
| [LICENSE](../LICENSE) | MIT license |
