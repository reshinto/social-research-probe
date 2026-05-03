[Back to docs index](README.md)


# Design Patterns

The codebase uses a few repeated patterns. Learn these first; most extension work is one of them.

## Pipeline Pattern

![Pipeline pattern](diagrams/dp_pipeline.svg)

A platform pipeline is an ordered list of stage groups. Each stage reads `PipelineState` and writes a named output. Stage groups with multiple stages run concurrently.

## Adapter Pattern

![Adapter pattern](diagrams/dp_adapter.svg)

Technologies hide external details. YouTube API calls, CLI runners, search providers, chart rendering, TTS, exports, and SQLite persistence are all technology adapters. Services call `tech.execute(input)` and consume project-shaped outputs.

## Strategy Pattern

![Strategy pattern](diagrams/dp_strategy.svg)

Config selects strategies at runtime: classification provider, corroboration provider, LLM runner, and optional local or hosted execution. The caller asks a registry or service for the selected behavior instead of importing one vendor everywhere.

## Registry Pattern

![Registry pattern](diagrams/dp_registry.svg)

Platform and runner lookup use registries. The pipeline registry exposes `youtube` and `all`. The LLM registry imports concrete runner modules, then maps runner names to classes.

## Fake Seam

![Fake seam](diagrams/dp_fake_seam.svg)

Tests avoid live APIs. The orchestrator can register fake YouTube behavior when `SRP_TEST_USE_FAKE_YOUTUBE=1`, and tests use fixture data for provider-like behavior.

## Result Objects

`TechResult` records technology name, input, output, success flag, and error. `ServiceResult` records service name, input key, and technology results. These objects preserve partial failure details without forcing every stage to parse exceptions.
