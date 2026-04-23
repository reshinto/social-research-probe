---
name: srp
description: Evidence-first social-media research via the `srp` CLI. Handles topics, purposes, suggestions, and research runs.
---

Use `srp` as the source of truth for every command and state change. Shell to `srp`; never invent command syntax; load the matching reference from `references/index.md` and follow it exactly.

When `llm.runner = none`, use the host LLM for the skill-only reasoning steps: classify natural-language research requests, summarize sections 1-9 from the packet/report, and author Compiled Synthesis, Opportunity Analysis, and Final Summary when the CLI leaves them blank.

When `llm.runner` is set to `claude`, `gemini`, `codex`, or `local`, prefer the CLI-produced LLM output and do not duplicate it with the host model.

On non-zero exit surface stderr + exit code.

See `references/index.md` for the command map.
