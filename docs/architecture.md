[Back to docs index](README.md)


# Architecture

![Component map](diagrams/components.svg)

The source tree separates command parsing, command behavior, platform orchestration, service coordination, technology adapters, and shared utilities.

## Layers

| Layer | Package | Responsibility |
| --- | --- | --- |
| CLI | `social_research_probe/cli` | Build `argparse` parsers and dispatch namespaces. |
| Commands | `social_research_probe/commands` | Implement user-facing operations. |
| Config | `social_research_probe/config.py` | Resolve data directory, merge config, expose gates. |
| Platforms | `social_research_probe/platforms` | Register pipelines and own stage order. |
| Services | `social_research_probe/services` | Run batches, choose technologies, normalize results. |
| Technologies | `social_research_probe/technologies` | API calls, CLI runners, renderers, algorithms, persistence. |
| Utils | `social_research_probe/utils` | Types, cache, state, display, claims, narratives, report helpers. |

![Architecture interaction](diagrams/architecture_interaction.svg)

## Runtime State

`PipelineState` is the shared mutable state passed through stages. It contains `platform_type`, parsed command object, optional cache field, `platform_config`, `inputs`, and `outputs`.

Stages write with `set_stage_output(stage, data)` and read with `get_stage_output(stage)`. The final report is also stored at `state.outputs["report"]`.

## Base Contracts

`BaseStage.run()` sets stage-specific cache bypass context and calls `execute()`. `stage_name` is the config and state key.

`BaseService` owns `execute_batch()` and `execute_one()`. Subclasses must implement `_get_technologies()` and `execute_service()`. Overriding `execute_batch` or `execute_one` raises `TypeError` at class definition time.

`BaseTechnology` owns flag checks, cache, timing, exception isolation, and `_cache_key()`. Subclasses implement `_execute()`.

## Current Pipeline

![Data flow](diagrams/data-flow.svg)

The concrete YouTube pipeline is source-specific, but most work is delegated to reusable services and technologies. This lets a future platform reuse scoring, statistics, charts, claims, narratives, reporting, exports, and persistence after it normalizes item fields.
