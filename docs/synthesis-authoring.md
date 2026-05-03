[Back to docs index](README.md)


# Synthesis Authoring

The synthesis stage builds a context from narratives, corroboration, scores, fetched items, stats, and charts. `SynthesisService` delegates to `SynthesisTech` when LLM synthesis is enabled.

## What Synthesis Should Do

Synthesis should connect evidence. It can summarize patterns across top-ranked items, mention corroboration status, note warnings, and explain opportunities or risks. It should not invent sources that are not in the report dictionary.

## Structured Sections

After `assemble`, `structured_synthesis_stage.py` can attach structured sections such as compiled synthesis, opportunity analysis, and final summary. The `report` command can also re-render HTML from a saved packet while replacing those sections from files.

## Manual Editing Rules

When editing generated synthesis, keep source references and uncertainty. If claims are weak or uncorroborated, preserve that limitation. Use the CSV exports and SQLite claim records to audit specific statements.
