[Back to docs index](README.md)


# Model Applicability

The code uses model runners only for tasks that benefit from generated or structured text. Deterministic code owns fetching, config, cache, scoring, statistics, chart selection, export file names, and SQLite schema.

## Good Runner Tasks

| Task | Why a runner helps |
| --- | --- |
| Natural-language query classification | Converts one query string into topic and purpose. |
| Source classification fallback | Helps when heuristics return `unknown`. |
| Summaries | Compresses transcripts or source text. |
| Claim extraction with `use_llm = true` | Can extract more nuanced claims, then falls back to deterministic extraction. |
| Synthesis | Connects evidence into narrative sections. |
| Runner-backed search | Lets LLM tools provide citations when supported. |

## Poor Runner Tasks

Do not use runners to decide whether config gates are enabled, where files live, how database migrations run, or what sources were fetched. Those are deterministic source-code responsibilities.
