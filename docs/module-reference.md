[Back to docs index](README.md)

# Module Reference

![Module map](diagrams/components.svg)

This page explains where to look before editing the code. The repository is organized by responsibility rather than by vendor. A new feature usually touches a command, one or more services, and one or more technologies; it should not scatter logic across unrelated layers.

For repository-level files such as `pyproject.toml`, `Makefile`, `VERSION`,
workflow files, and example config files, see [Root Files](root-files.md).

## Root package

| Path | Responsibility |
| --- | --- |
| `social_research_probe/cli` | Argparse setup and command dispatch. |
| `social_research_probe/commands` | User-facing command implementations. |
| `social_research_probe/config.py` | Defaults, config loading, data-dir resolution, gates. |
| `social_research_probe/platforms` | Platform contracts, registry, orchestrator, and pipelines. |
| `social_research_probe/services` | Task orchestration such as scoring, enrichment, analysis, synthesis, reporting. |
| `social_research_probe/technologies` | Atomic adapters and pure algorithms. |
| `social_research_probe/utils` | Cache, state, parsing, display, secrets, IO, and validation helpers. |
| `tests` | Unit, integration, contract, and eval tests. |
| `docs` | Human documentation and diagram sources. |

## Naming rule

Services coordinate work. Technologies perform one concrete operation. Platforms decide stage order. Commands are the CLI surface. Utils are shared support code that should not own product behavior.

## How to use this map

If you are adding a user-facing flag or command, start in `cli` and `commands`. If you are changing what happens during a research run, start in `platforms` to understand stage order, then move into the relevant `services` package. If you are integrating a provider, runner, parser, renderer, or algorithm, put the concrete implementation under `technologies` and keep the service focused on orchestration.

Avoid putting product behavior in `utils`. A utility should be reusable support code such as cache IO, path handling, display helpers, or validation. If a helper starts making research decisions, it likely belongs in a service or technology module instead.

## Example change paths

| Change | Likely files |
| --- | --- |
| Add a new CLI subcommand. | `cli/parsers.py`, `commands/*`, tests under `tests/unit` or `tests/integration`. |
| Add a new platform. | `platforms/*`, platform config defaults, fake platform tests, report integration tests. |
| Add a new corroboration provider. | `technologies/corroboration/*`, `services/corroborating/*`, config gates, secret handling tests. |
| Change chart output. | `services/reporting/charts.py`, chart technology helpers, chart docs, diagram/docs tests. |
| Change report assembly. | analysis/synthesis/reporting services and packet contract tests. |
