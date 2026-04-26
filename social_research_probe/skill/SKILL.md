---
name: srp
description: Manual srp CLI operator for evidence-first social-media research.
disable-model-invocation: true
---

Use only when user invokes `/srp`.

Rules:
- CLI is truth. Prefer `srp ...`; do not invent flags.
- Load [references/index.md](references/index.md), then one matching ref only.
- For secrets, use `srp config set-secret`; never ask for keys in chat.
- Nonzero exit: show stderr + exit code.

$ARGUMENTS
