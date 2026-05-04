[Back to docs index](README.md)


# Adding A Platform

![Add platform flow](diagrams/add_platform_flow.svg)

A platform owns source-specific fetching and stage order. Shared services and technologies should be reused when item data can be normalized into the existing shapes.

## Contract

A concrete platform pipeline should implement `BaseResearchPlatform.run(state)` and usually expose a `stages()` method that returns ordered `BaseStage` groups. A stage subclass must implement `stage_name` and `execute(state)`.

![Platform contract](diagrams/add_platform_contract.svg)

## Required Work

1. Create `social_research_probe/platforms/<name>/`.
2. Add stage classes for source-specific steps.
3. Normalize source items so shared scoring and reporting can read fields such as `id`, `url`, `title`, `channel`, `published_at`, `description`, `metrics`, `scores`, `features`, and `extras`.
4. Register the pipeline in the platform registry path used by `PIPELINES`.
5. Add `[platforms.<name>]`, `[stages.<name>]`, service gates, and technology gates to `DEFAULT_CONFIG` and `config.toml.example`.
6. Add unit tests for stage state transitions and integration tests for an offline fixture run.
7. Update docs and diagrams.

## Reuse Rules

Reuse scoring, statistics, charts, claims, narratives, exports, and SQLite persistence when the platform can supply compatible dictionaries. Write new services or technologies only for genuinely platform-specific behavior.

## Common Mistakes

| Mistake | Why it fails |
| --- | --- |
| Putting provider API calls in a stage | Stages become hard to test and cannot reuse technology cache/error behavior. |
| Skipping config gates | Operators lose cost and availability control. |
| Returning platform-specific objects past scoring | Shared services expect normalized dictionaries. |
| Writing directly to reports from early stages | Later export and persistence stages lose audit context. |
