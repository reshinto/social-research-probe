All suggestion commands stage into pending.

- Topics: `srp suggest-topics [--count N] [--output text|json|markdown]`
  - If no LLM runner, deterministic seed pool is used.
- Purposes: `srp suggest-purposes [--count N] [--output ...]`
  - Requires configured structured LLM runner.
- Stage JSON from stdin: `srp stage-suggestions --from-stdin [--output ...]`

Stage JSON shape:
```json
{"topic_candidates":[{"value":"...","reason":"..."}],"purpose_candidates":[{"name":"...","method":"...","evidence_priorities":[]}]}
```
