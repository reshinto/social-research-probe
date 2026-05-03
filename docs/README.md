# Documentation

This documentation is the operating manual and learning path for Social Research Probe. Read it in order if you are new. Use the reference pages when you are changing a specific layer.

The current concrete platform is YouTube. The architecture is platform-oriented, so the code separates platform stages from reusable services, technology adapters, scoring, analysis, reporting, cache, config, and persistence.

## Learning Path

| Step | Read | What you learn |
| --- | --- | --- |
| 1 | [Objective](objective.md) | What problem the project solves and what a good run should answer. |
| 2 | [How it works](how-it-works.md) | The end-to-end runtime flow from CLI input to report/export/database output. |
| 3 | [Installation](installation.md) | Python environment, package install, data directory, secrets, and optional providers. |
| 4 | [Usage](usage.md) | Day-to-day command workflow and how to read a run. |
| 5 | [Configuration](configuration.md) | Config files, secrets, gates, runners, and provider controls. |
| 6 | [Data directory](data-directory.md) | Where config, state, cache, reports, exports, charts, and SQLite data live. |
| 7 | [Architecture](architecture.md) | Package boundaries and the Platform -> Service -> Technology contract. |
| 8 | [Module reference](module-reference.md) | Where to look before editing code. |
| 9 | [Python language guide](python-language-guide.md) | Python fundamentals and repository-specific Python patterns. |

## User Reference

| Topic | Document |
| --- | --- |
| Command examples | [Commands](commands.md) |
| API keys and cost control | [API costs and keys](api-costs-and-keys.md) |
| LLM runner setup | [LLM runners](llm-runners.md) |
| Source classification | [Source classification](classifying.md) |
| Claim corroboration | [Corroboration](corroboration.md) |
| Scoring model | [Scoring](scoring.md) |
| Statistics | [Statistics](statistics.md) |
| Charts | [Charts](charts.md) |
| Summary quality | [Summary quality](summary-quality-report.md) |
| Synthesis authoring | [Synthesis authoring](synthesis-authoring.md) |
| Security | [Security](security.md) |
| Runtime dependencies | [Runtime dependencies](runtime-dependencies.md) |
| Model applicability | [Model applicability](model-applicability.md) |
| Cost optimization | [Cost optimization](cost-optimization.md) |

## Developer Reference

| Topic | Document |
| --- | --- |
| Design patterns | [Design patterns](design-patterns.md) |
| Root files | [Root files](root-files.md) |
| Testing | [Testing](testing.md) |
| LLM reliability harness | [LLM reliability harness](llm-reliability-harness.md) |
| Add a platform | [Adding a platform](adding-a-platform.md) |
| Add a service | [Adding a service](adding-a-service.md) |
| Add a technology | [Adding a technology](adding-a-technology.md) |

## Diagram Index

Every rendered SVG under `docs/diagrams/` has a matching Mermaid source under `docs/diagrams/src/`.

| Diagram | Used for |
| --- | --- |
| ![System context](diagrams/context.svg) | System boundary and external actors. |
| ![Component map](diagrams/components.svg) | Source package responsibilities. |
| ![Data flow](diagrams/data-flow.svg) | YouTube research data path. |
| ![Research sequence](diagrams/research-sequence.svg) | Runtime call order. |
| ![Async fan-out](diagrams/async-fanout.svg) | Parallel stage behavior. |
| ![Configuration lifecycle](diagrams/config_lifecycle.svg) | Config, secrets, and gates. |
| ![Cost control flow](diagrams/cost_flow.svg) | Cache and provider budget controls. |
| ![Corroboration flow](diagrams/corroboration_flow.svg) | Claim checking. |
| ![Runner agnostic search](diagrams/corroboration-runner-agnostic.svg) | LLM search contract. |
| ![Runner selection](diagrams/runner_choice.svg) | Runner fallback and health checks. |
| ![Reliability harness](diagrams/reliability-harness.svg) | Evaluation flow. |
| ![Summary quality flow](diagrams/summary-quality.svg) | Summary generation and quality checks. |
| ![Testing pyramid](diagrams/testing-pyramid.svg) | Test strategy. |
| ![Release pipeline](diagrams/release-pipeline.svg) | Release workflow. |
| ![Extension map](diagrams/roadmap.svg) | Future platform extension shape. |
| ![Platform contract](diagrams/add_platform_contract.svg) | Platform boundary. |
| ![Add platform flow](diagrams/add_platform_flow.svg) | Platform extension steps. |
| ![Strategy pattern](diagrams/dp_strategy.svg) | Strategy pattern. |
| ![Adapter pattern](diagrams/dp_adapter.svg) | Adapter pattern. |
| ![Registry pattern](diagrams/dp_registry.svg) | Registry pattern. |
| ![Pipeline pattern](diagrams/dp_pipeline.svg) | Pipeline pattern. |
| ![Fake seam](diagrams/dp_fake_seam.svg) | Test seam. |
| ![Scoring model](diagrams/scoring-model.svg) | Ranking math. |
| ![Cache layout](diagrams/cache-layout.svg) | Data directory storage layout. |
| ![Python flow](diagrams/python-flow.svg) | Python primer. |
| ![Service technology](diagrams/service-technology.svg) | Service execution lifecycle. |
| ![Command surface](diagrams/command-surface.svg) | CLI overview. |
| ![Security boundaries](diagrams/security-boundaries.svg) | Secrets and trust boundaries. |
| ![Report outputs](diagrams/report-outputs.svg) | Output artifacts. |
| ![System tradeoffs](diagrams/system-tradeoffs.svg) | Architecture choices. |
| ![Chart suite](diagrams/chart-suite.svg) | Chart data flow. |
| ![Statistics suite](diagrams/statistics-suite.svg) | Statistics data flow. |
| ![Statistics interpretation](diagrams/statistics-interpretation.svg) | Reading statistics. |
| ![API cost map](diagrams/api-cost-map.svg) | Provider and runner cost boundaries. |
| ![Architecture interaction](diagrams/architecture_interaction.svg) | Platform/Service/Technology flow. |
| ![Add service interaction](diagrams/add_service_interaction.svg) | Adding a service. |
| ![Classification flow](diagrams/classifying_flow.svg) | Source classification. |
| ![Narration flow](diagrams/narration_flow.svg) | Audio narration. |
