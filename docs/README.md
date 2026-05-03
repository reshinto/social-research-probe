# Documentation

This directory is the operating manual for the code in `social_research_probe/`. The content is organized as a learning path, then reference material for specific subsystems.

## Learning Path

| Step | Document | Source-code anchor |
| --- | --- | --- |
| 1 | [Objective](objective.md) | `README.md`, `commands/research.py`, `platforms/orchestrator.py` |
| 2 | [How it works](how-it-works.md) | `platforms/youtube/__init__.py` |
| 3 | [Installation](installation.md) | `pyproject.toml`, `commands/setup.py`, `commands/config.py` |
| 4 | [Usage](usage.md) | `cli/parsers.py`, `commands/research.py` |
| 5 | [Commands](commands.md) | `commands/__init__.py`, `cli/parsers.py` |
| 6 | [Configuration](configuration.md) | `config.py`, `config.toml.example` |
| 7 | [Data directory](data-directory.md) | `config.py`, `utils/caching/pipeline_cache.py`, export and persistence technologies |
| 8 | [Architecture](architecture.md) | `platforms`, `services`, `technologies`, `utils` |
| 9 | [Python language guide](python-language-guide.md) | Python constructs used across the package |

## User Reference

| Topic | Document |
| --- | --- |
| API keys and cost boundaries | [API costs and keys](api-costs-and-keys.md) |
| Runtime model runners | [LLM runners](llm-runners.md) |
| Source classification | [Source classification](classifying.md) |
| Claim corroboration | [Corroboration](corroboration.md) |
| Scoring math | [Scoring](scoring.md) |
| Statistics | [Statistics](statistics.md) |
| Charts | [Charts](charts.md) |
| Summary behavior | [Summary quality](summary-quality-report.md) |
| Synthesis editing | [Synthesis authoring](synthesis-authoring.md) |
| Security | [Security](security.md) |
| Runtime dependencies | [Runtime dependencies](runtime-dependencies.md) |
| Model selection | [Model applicability](model-applicability.md) |
| Cost control | [Cost optimization](cost-optimization.md) |

## Developer Reference

| Topic | Document |
| --- | --- |
| Package map | [Module reference](module-reference.md) |
| Design patterns | [Design patterns](design-patterns.md) |
| Root files | [Root files](root-files.md) |
| Testing | [Testing](testing.md) |
| Evaluation harness | [LLM reliability harness](llm-reliability-harness.md) |
| Add a platform | [Adding a platform](adding-a-platform.md) |
| Add a service | [Adding a service](adding-a-service.md) |
| Add a technology | [Adding a technology](adding-a-technology.md) |

## Diagram Index

Every diagram below is checked in as SVG so Markdown renderers can display it directly. Every SVG has a Mermaid source under `docs/diagrams/src/`.

| Diagram | Source concept |
| --- | --- |
| ![System context](diagrams/context.svg) | Users, local files, YouTube, runners, evidence providers. |
| ![Component map](diagrams/components.svg) | Package-level responsibilities. |
| ![Data flow](diagrams/data-flow.svg) | YouTube research packet flow. |
| ![Research sequence](diagrams/research-sequence.svg) | CLI to platform to outputs. |
| ![Async fanout](diagrams/async-fanout.svg) | Concurrent stage and service execution. |
| ![Config lifecycle](diagrams/config_lifecycle.svg) | Defaults, config file, secrets, environment. |
| ![Cost flow](diagrams/cost_flow.svg) | Cost gates before provider calls. |
| ![Corroboration flow](diagrams/corroboration_flow.svg) | Claims through provider verdicts. |
| ![Runner agnostic search](diagrams/corroboration-runner-agnostic.svg) | Runner-backed search provider. |
| ![Runner choice](diagrams/runner_choice.svg) | Runner registry and fallback. |
| ![Reliability harness](diagrams/reliability-harness.svg) | Evaluation files and reports. |
| ![Summary quality](diagrams/summary-quality.svg) | Text surrogate to summary. |
| ![Testing pyramid](diagrams/testing-pyramid.svg) | Contract, unit, integration, eval tests. |
| ![Release pipeline](diagrams/release-pipeline.svg) | Version, tests, package, publish. |
| ![Extension map](diagrams/roadmap.svg) | Future platform expansion points. |
| ![Platform contract](diagrams/add_platform_contract.svg) | Required platform behavior. |
| ![Add platform flow](diagrams/add_platform_flow.svg) | Platform implementation steps. |
| ![Strategy pattern](diagrams/dp_strategy.svg) | Runtime provider choice. |
| ![Adapter pattern](diagrams/dp_adapter.svg) | Technology boundaries. |
| ![Registry pattern](diagrams/dp_registry.svg) | Platform and runner lookup. |
| ![Pipeline pattern](diagrams/dp_pipeline.svg) | PipelineState stage handoff. |
| ![Fake seam](diagrams/dp_fake_seam.svg) | Test replacement points. |
| ![Scoring model](diagrams/scoring-model.svg) | Trust, trend, opportunity, overall. |
| ![Cache layout](diagrams/cache-layout.svg) | Data directory and cache tree. |
| ![Python flow](diagrams/python-flow.svg) | Python concepts used by the repo. |
| ![Service technology](diagrams/service-technology.svg) | BaseService and BaseTechnology lifecycle. |
| ![Command surface](diagrams/command-surface.svg) | Top-level and hidden command groups. |
| ![Security boundaries](diagrams/security-boundaries.svg) | Secret and data movement. |
| ![Report outputs](diagrams/report-outputs.svg) | HTML, exports, SQLite. |
| ![System tradeoffs](diagrams/system-tradeoffs.svg) | Main architecture tradeoffs. |
| ![Chart suite](diagrams/chart-suite.svg) | Chart renderers. |
| ![Statistics suite](diagrams/statistics-suite.svg) | Statistical selector. |
| ![Statistics interpretation](diagrams/statistics-interpretation.svg) | How to read generated statistics. |
| ![API cost map](diagrams/api-cost-map.svg) | Provider cost categories. |
| ![Architecture interaction](diagrams/architecture_interaction.svg) | Platform, service, technology interaction. |
| ![Add service interaction](diagrams/add_service_interaction.svg) | Service extension lifecycle. |
| ![Classification flow](diagrams/classifying_flow.svg) | Heuristic, LLM, and hybrid classifiers. |
| ![Narration flow](diagrams/narration_flow.svg) | Audio report path. |
