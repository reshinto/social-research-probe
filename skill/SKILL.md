---
name: SocialResearchProbe
description: Evidence-first social-media research via the `srp` CLI. Triggers on
  update-topics, update-purposes, show-topics, show-purposes, suggest-topics,
  suggest-purposes, show-pending-suggestions, apply-pending-suggestions,
  discard-pending-suggestions, run-research.
---

# SocialResearchProbe

Shell out to `srp`; never reimplement logic. Always pass `--mode skill` so the CLI
emits a packet instead of calling an external LLM.

## Command → reference

| User command                    | Reference file                        |
|---------------------------------|---------------------------------------|
| update-topics                   | references/update-topics.md           |
| show-topics                     | references/show-topics.md             |
| update-purposes                 | references/update-purposes.md         |
| show-purposes                   | references/show-purposes.md           |
| suggest-topics                  | references/suggest-topics.md          |
| suggest-purposes                | references/suggest-purposes.md        |
| show-pending-suggestions        | references/show-pending.md            |
| apply-pending-suggestions       | references/apply-pending.md           |
| discard-pending-suggestions     | references/discard-pending.md         |
| run-research                    | references/run-research.md            |

1. Identify the user's command.
2. Read the matching reference file.
3. Follow its instructions exactly.
4. Report CLI stdout verbatim. On non-zero exit surface stderr + exit code.
