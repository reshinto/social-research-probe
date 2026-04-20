# social-research-probe Documentation

[Home](README.md)

`srp` is an evidence-first social-media research CLI that fetches YouTube content, scores it by trust and trend signals, auto-corroborates claims, generates LLM synthesis, and renders an HTML report — all from a single command.

---

## For New Users

| Document | Description |
|---|---|
| [Installation](installation.md) | Install from PyPI or source, configure secrets, verify setup |
| [Usage Guide](usage.md) | Run your first research, understand topics/purposes, view reports |
| [Command Reference](commands.md) | Every command, flag, and exit code |

---

## For Operators

| Document | Description |
|---|---|
| [Security](security.md) | Threat model, secret storage, network egress, hardening checklist |
| [Command Reference](commands.md) | Config subcommands, secret management, environment variables |

---

## For Contributors

| Document | Description |
|---|---|
| [Architecture](architecture.md) | System design, module map, data flow, extension points |
| [Design Patterns](design-patterns.md) | Patterns used in the codebase (adapter, registry, strategy, pipeline) |
| [Python Language Guide](python-language-guide.md) | TypedDicts, protocols, async patterns, fixture conventions |
| [Testing](testing.md) | Test tiers, TDD workflow, coverage gate, fake adapters |

---

## Reference

| Document | Description |
|---|---|
| [model-applicability.md](model-applicability.md) | Which LLM models are recommended for which pipeline stages |
| [commands.md](commands.md) | Deep flag reference and exit-code table |

---

## Project Files

| File | Description |
|---|---|
| [CHANGELOG.md](../CHANGELOG.md) | Release history in Keep-a-Changelog format |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Development workflow, TDD rules, file-size limits, versioning |
| [SECURITY.md](../SECURITY.md) | Responsible disclosure policy |
| [LICENSE](../LICENSE) | MIT license |
