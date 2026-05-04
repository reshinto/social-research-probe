[Back to docs index](README.md)


# Summary Quality

![Summary quality](diagrams/summary-quality.svg)

Summaries are generated after the comments stage. Before summary generation, `TextSurrogateService` selects the best available text evidence and records evidence layer, evidence tier, penalties, and warnings. `SummaryService` then sends a bounded prompt through `SummaryEnsembleTech` when an LLM runner is configured.

## Source Of Truth

A summary is a compressed representation of item text. It should not be treated as stronger evidence than the transcript, description, comments, or source metadata that fed it.

## Failure Behavior

If text is empty, the runner is disabled, the runner fails, or structured output is invalid, the service returns no useful summary rather than stopping the whole pipeline. Later stages can still report source metadata, scoring, charts, and exports.

## Debug Checklist

1. Check whether `fetch_transcripts` was disabled by `--no-transcripts`.
2. Check whether text surrogate output has primary text.
3. Check `llm.runner` and the selected runner technology flag.
4. Check `cache/technologies/llm_ensemble` for repeated weak output.
5. Compare any generated summary against source text before trusting it.
