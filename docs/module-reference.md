[Back to docs index](README.md)


# Module Reference

Use this map before editing. It is based on package names and imports in `social_research_probe/`.

## Package Map

| Path | What belongs there |
| --- | --- |
| `cli/` | Parser and dispatch plumbing only. |
| `commands/` | User-facing commands and output formatting. |
| `platforms/` | Platform registry, `PipelineState`, base stage contracts, concrete pipelines. |
| `platforms/youtube/` | YouTube stage classes and stage order. |
| `platforms/all/` | Meta-pipeline over concrete platforms. |
| `services/` | Batch orchestration for sourcing, classifying, scoring, enriching, corroborating, analyzing, synthesizing, reporting, persistence, and LLM calls. |
| `technologies/` | Concrete adapters and algorithms behind feature flags. |
| `technologies/persistence/sqlite/` | SQLite connection, schema, repository writes, queries. |
| `utils/core/` | Shared types, errors, parsing, coercion, strings, report helpers. |
| `utils/state/` | JSON state files, schemas, migrations, validation. |
| `utils/claims/` | Claim extraction, LLM extraction, quality scoring, claim types. |
| `utils/narratives/` | Narrative cluster types, IDs, scoring, clustering. |
| `utils/llm/` | Runner registry, schemas, prompts, ensemble helpers. |
| `utils/demo/` | Synthetic data for `demo-report`. |
| `skill/` | Bundled operator skill installed by `srp install-skill`. |

## Where To Change Things

| Change | Primary files |
| --- | --- |
| Add CLI flag | `cli/parsers.py`, handler command module, tests. |
| Add a research stage | `platforms/<platform>/*_stage.py`, pipeline stage list, config gates. |
| Add reusable orchestration | `services/<area>/...`. |
| Add provider or algorithm | `technologies/<area>/...`. |
| Add persisted data | SQLite schema, repository, queries, persistence technology, tests. |
| Add report artifact | report renderer/export package, report stage, persistence if needed. |
| Add state file | `utils/state/schemas.py`, `utils/state/store.py`, command tests. |

## Reading Order For A Bug

1. Start at the command module if the symptom is CLI output or argument handling.
2. Move to the platform stage if the symptom is a missing stage output.
3. Move to the service if the symptom is normalization or fallback behavior.
4. Move to the technology if the symptom is provider-specific, rendering, caching, or persistence.
5. Move to utilities only when the same helper is shared across more than one layer.
