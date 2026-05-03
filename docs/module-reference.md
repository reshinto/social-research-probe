[Back to docs index](README.md)

# Module Reference

![Module map](diagrams/components.svg)

This page tells you where to look before editing. The repository is organized by responsibility, not by vendor.

## Root Package

| Path | Responsibility |
| --- | --- |
| `social_research_probe/__init__.py` | Version resolution from `VERSION`. |
| `social_research_probe/__main__.py` | `python -m social_research_probe` entry point. |
| `social_research_probe/config.py` | Default config, config loading, data-dir resolution, and gates. |
| `social_research_probe/cli/` | Argparse parser, CLI dispatch, and DSL parsing helpers. |
| `social_research_probe/commands/` | User-facing command implementations. |
| `social_research_probe/platforms/` | Platform contracts, registry, orchestrator, shared `PipelineState`, and platform pipelines. |
| `social_research_probe/platforms/youtube/` | Current concrete YouTube stage implementations. |
| `social_research_probe/platforms/all/` | Concurrent runner for all registered concrete platform pipelines. |
| `social_research_probe/services/` | Service lifecycle, `ServiceResult`, `TechResult`, and task orchestration. |
| `social_research_probe/technologies/` | Atomic adapters and algorithms: YouTube, transcripts, LLMs, corroboration, statistics, charts, report rendering, exports, persistence, TTS, validation. |
| `social_research_probe/utils/` | Shared types, state, cache, display, claims, narratives, report formatting, search query helpers, IO, secrets, and core parsing. |
| `social_research_probe/skill/` | Bundled `/srp` skill instructions and references installed by `srp install-skill`. |

## Tests And Docs

| Path | Responsibility |
| --- | --- |
| `tests/unit/` | Fast unit tests for commands, pure helpers, services, technologies, and packet contracts. |
| `tests/integration/` | End-to-end and subprocess-style checks for pipeline and CLI behavior. |
| `tests/contract/` | Repository rules such as docs links, diagrams, type constraints, and version consistency. |
| `tests/evals/` | LLM and summary quality harnesses. |
| `tests/fixtures/` | Fakes and golden fixtures. |
| `docs/` | Human docs, diagrams, and explanatory images. |
| `docs/diagrams/src/` | Mermaid diagram sources. |
| `docs/diagrams/*.svg` | Rendered diagrams that must match `.mmd` source names. |

## Naming Rule

| Name | Meaning |
| --- | --- |
| Command | User-facing operation called from the CLI. |
| Platform | Source-specific stage order and source adapter boundary. |
| Stage | One named step in a platform pipeline. |
| Service | Reusable task coordinator that returns `ServiceResult`. |
| Technology | One concrete provider call, renderer, persistence write, CLI invocation, or pure algorithm. |
| Utility | Shared support code that does not own product decisions. |

## Change Map

| Change | Likely files |
| --- | --- |
| Add or change a CLI command | `cli/parsers.py`, `cli/handlers.py`, `commands/<name>.py`, command tests, [Commands](commands.md). |
| Change research stage order | `platforms/youtube/__init__.py`, relevant stage tests, [How it works](how-it-works.md), diagrams. |
| Add a YouTube stage | `platforms/youtube/<stage>_stage.py`, config defaults/gates, tests, docs. |
| Add a new platform | `platforms/<name>/`, platform registry/pipeline export, config defaults, fake tests, [Adding a platform](adding-a-platform.md). |
| Add a service | `services/<domain>/`, one or more technologies, a platform stage, config gates, [Adding a service](adding-a-service.md). |
| Add a technology | `technologies/<domain>/`, config technology gate, health checks if needed, [Adding a technology](adding-a-technology.md). |
| Change scoring | `technologies/scoring/`, `services/scoring/`, scoring tests, [Scoring](scoring.md), scoring diagram. |
| Change source classification | `technologies/classifying/`, `services/classifying/`, `utils/core/classifying.py`, [Source classification](classifying.md). |
| Change claims or narratives | `utils/claims/`, `technologies/claims/`, `utils/narratives/`, persistence/export/report tests. |
| Change corroboration | `technologies/corroborates/`, `services/corroborating/`, secret checks, [Corroboration](corroboration.md). |
| Change chart output | `technologies/charts/`, `services/analyzing/charts.py`, [Charts](charts.md), chart diagram. |
| Change report rendering | `utils/report/`, `technologies/report_render/`, `services/reporting/`, report/export tests. |
| Change SQLite persistence | `technologies/persistence/sqlite/`, `services/persistence/`, DB commands/tests, [Data directory](data-directory.md). |
| Change skill behavior | `social_research_probe/skill/`, `commands/install_skill.py`, skill bundle tests. |

## Reading A File

When opening a new file, identify four things first:

1. Which layer it belongs to.
2. Which input shape it expects.
3. Which output shape it promises.
4. Which config gates or environment variables can disable it.

If a function starts mixing layers, stop and move code to the correct boundary. A platform stage can choose when to run a service. A service can choose which technology to run. A technology can know provider details. A utility should stay generic.
