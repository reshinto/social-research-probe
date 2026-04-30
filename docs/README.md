# Documentation

Start here if you have never used Social Research Probe before. The docs are organized like a small system design guide: begin with the problem, then the workflow, architecture, tradeoffs, commands, and extension points. The goal is that a reader can understand what the project does, why the code is shaped this way, and how to run or extend it without having to infer missing context from source files.

The project is platform-oriented, not YouTube-oriented. YouTube is the first implemented source adapter. The shared pipeline is intentionally written so future adapters can support TikTok, Instagram, X, web search, RSS, forums, and other public sources while reusing scoring, statistics, corroboration, synthesis, reporting, cache, and configuration behavior.

## Learning path

| Step | Read | Purpose |
| --- | --- | --- |
| 1 | [Objective](objective.md) | Why the project exists and what problem it solves. |
| 2 | [How it works](how-it-works.md) | Plain-English walkthrough of one research run. |
| 3 | [Usage](usage.md) | Commands for daily use. |
| 4 | [Configuration](configuration.md) | How config, secrets, gates, and data directories work. |
| 5 | [Architecture](architecture.md) | System design, diagrams, and tradeoffs. |
| 6 | [Design patterns](design-patterns.md) | The code patterns used in the repository. |

After those six pages, read the reference pages only when you need the matching task. For example, read [Commands](commands.md) when you need exact input and output examples, [Charts](charts.md) when you need to interpret PNG outputs, and [Adding a platform](adding-a-platform.md) when you want to add a new source.

## Reference

| Topic | Document |
| --- | --- |
| Install | [Installation](installation.md) |
| Commands | [Commands](commands.md) |
| Classification | [Source classification](classifying.md) |
| Corroboration | [Corroboration](corroboration.md) |
| LLM runners | [LLM runners](llm-runners.md) |
| API costs and keys | [API costs and keys](api-costs-and-keys.md) |
| Data directory | [Data directory](data-directory.md) |
| Runtime dependencies | [Runtime dependencies](runtime-dependencies.md) |
| Root files | [Root files](root-files.md) |
| Scoring | [Scoring](scoring.md) |
| Statistics | [Statistics](statistics.md) |
| Charts | [Charts](charts.md) |
| Synthesis | [Synthesis authoring](synthesis-authoring.md) |
| Summary quality | [Summary quality](summary-quality-report.md) |
| Reliability harness | [LLM reliability harness](llm-reliability-harness.md) |
| Model applicability | [Model applicability](model-applicability.md) |
| Cost optimization | [Cost optimization](cost-optimization.md) |
| Module map | [Module reference](module-reference.md) |
| Add a platform | [Adding a platform](adding-a-platform.md) |
| Add a service | [Adding a service](adding-a-service.md) |
| Add a technology | [Adding a technology](adding-a-technology.md) |
| Python primer | [Python language guide](python-language-guide.md) |
| Testing | [Testing](testing.md) |
| Security | [Security](security.md) |

## Diagram index

These SVGs are rendered from `docs/diagrams/src/*.mmd` with a white background for readability in dark-mode viewers.

| Diagram | Used for |
| --- | --- |
| ![System context](diagrams/context.svg) | System boundary |
| ![Component map](diagrams/components.svg) | Package layout |
| ![Data flow](diagrams/data-flow.svg) | Research data path |
| ![Research sequence](diagrams/research-sequence.svg) | Runtime call order |
| ![Async fan-out](diagrams/async-fanout.svg) | Parallel stage behavior |
| ![Configuration lifecycle](diagrams/config_lifecycle.svg) | Config and gates |
| ![Cost control flow](diagrams/cost_flow.svg) | Cache and LLM budget |
| ![Corroboration flow](diagrams/corroboration_flow.svg) | Claim checks |
| ![Runner agnostic search](diagrams/corroboration-runner-agnostic.svg) | LLM search contract |
| ![Runner selection](diagrams/runner_choice.svg) | LLM runner fallback |
| ![Reliability harness](diagrams/reliability-harness.svg) | Evaluation flow |
| ![Summary quality flow](diagrams/summary-quality.svg) | Summary generation |
| ![Testing pyramid](diagrams/testing-pyramid.svg) | Test strategy |
| ![Release pipeline](diagrams/release-pipeline.svg) | CI/release shape |
| ![Extension map](diagrams/roadmap.svg) | How new sources fit |
| ![Platform contract](diagrams/add_platform_contract.svg) | Adapter boundary |
| ![Add platform flow](diagrams/add_platform_flow.svg) | Extension steps |
| ![Strategy pattern](diagrams/dp_strategy.svg) | Design pattern |
| ![Adapter pattern](diagrams/dp_adapter.svg) | Design pattern |
| ![Registry pattern](diagrams/dp_registry.svg) | Design pattern |
| ![Pipeline pattern](diagrams/dp_pipeline.svg) | Design pattern |
| ![Fake seam](diagrams/dp_fake_seam.svg) | Test seam |
| ![Scoring model](diagrams/scoring-model.svg) | Ranking math |
| ![Cache layout](diagrams/cache-layout.svg) | Filesystem state |
| ![Python flow](diagrams/python-flow.svg) | Python primer |
| ![Service technology](diagrams/service-technology.svg) | Service execution |
| ![Command surface](diagrams/command-surface.svg) | CLI overview |
| ![Security boundaries](diagrams/security-boundaries.svg) | Secrets and trust |
| ![Report outputs](diagrams/report-outputs.svg) | Output artifacts |
| ![System tradeoffs](diagrams/system-tradeoffs.svg) | Architecture choices |
| ![Chart suite](diagrams/chart-suite.svg) | Chart-specific data flow |
| ![Statistics suite](diagrams/statistics-suite.svg) | Statistics data flow |
| ![Statistics interpretation](diagrams/statistics-interpretation.svg) | Statistics interpretation |
| ![API cost map](diagrams/api-cost-map.svg) | API keys, free paths, and paid paths |
| ![Architecture interaction](diagrams/architecture_interaction.svg) | Platform/Service/Technology flow |
| ![Add service interaction](diagrams/add_service_interaction.svg) | Adding a new service |
| ![Classification flow](diagrams/classifying_flow.svg) | Source classification pipeline |
| ![Narration flow](diagrams/narration_flow.svg) | TTS narration pipeline |
