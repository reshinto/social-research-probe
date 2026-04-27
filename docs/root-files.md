[Back to docs index](README.md)

# Root Files

This page explains the files and folders at the repository root. Use it when you
open the project for the first time and need to know what each top-level item is
for, whether it is source-controlled, and when you should edit it.

The root directory contains project metadata, packaging configuration, workflow
automation, contributor policy files, and convenience scripts. Product behavior
mostly lives under `social_research_probe/`; tests live under `tests/`; human
documentation lives under `docs/`.

## Source-controlled root files

| File | Purpose | What it does | When to edit |
| --- | --- | --- | --- |
| `README.md` | Project entry point. | Introduces the project, quickstart, common commands, and key docs. | Update when the project positioning, command examples, or main docs links change. Preserve the badge area at the top. |
| `CHANGELOG.md` | Release history. | Records notable added, changed, fixed, and removed work under `Unreleased` or a version section. | Update when user-visible behavior, docs, CLI output, packaging, or workflows change. |
| `LICENSE` | Legal license. | Declares the MIT license for the project. | Rarely. Only change with explicit project/legal intent. |
| `CODE_OF_CONDUCT.md` | Community behavior policy. | Defines expected conduct for contributors and maintainers. | Rarely. Update only when governance policy changes. |
| `CONTRIBUTING.md` | Contributor workflow. | Explains how to set up, test, and contribute to the project. | Update when development workflow, test expectations, or contribution rules change. |
| `SECURITY.md` | Security disclosure policy. | Tells users how to report vulnerabilities and what versions are supported. | Update when support policy or disclosure process changes. |
| `VERSION` | Package version source of truth. | Hatch reads this file through `pyproject.toml`; the release workflow tags releases from it. | Edit only when intentionally preparing a release. |
| `pyproject.toml` | Python project configuration. | Defines package metadata, dependencies, console script entry point, build backend, pytest config, coverage config, and Ruff lint settings. | Edit when dependencies, packaging, script entry points, lint rules, or test config change. |
| `uv.lock` | Locked dependency resolution for uv users. | Pins the resolved dependency graph for reproducible installs with uv. | Regenerate when dependency constraints change and uv lock state needs updating. |
| `requirements.txt` | Runtime dependency list for pip-style workflows. | Lists runtime dependencies for users who install from requirements instead of project metadata. | Keep aligned with runtime dependencies in `pyproject.toml`. |
| `requirements-dev.txt` | Development dependency list for pip-style workflows. | Lists test/lint/dev dependencies for non-extra workflows. | Keep aligned with `[project.optional-dependencies].dev` in `pyproject.toml`. |
| `config.toml.example` | Example application config. | Documents default user-facing config shape: LLM runner, scoring weights, platform limits, stages, services, technologies, tunables, and reporting defaults. | Update when config keys are added, renamed, or behavior changes. Do not put secrets here. |
| `.env.example` | Example environment variables. | Documents secret env vars, provider keys, data-dir overrides, logging flags, fast mode, and cache disabling. | Update when environment variables are added, renamed, or removed. Do not put real secrets here. |
| `.gitignore` | Git ignore rules. | Prevents generated files, local environments, caches, logs, data directories, and editor files from being committed. | Update when new generated artifacts or local-only files appear. |
| `Makefile` | Developer command shortcuts. | Provides common test and eval commands such as `make test`, `make test-fast`, and `make eval-summary-quality`. | Update when developer workflows change or a repeated command deserves a shortcut. |
| `install.sh` | Convenience local install script. | Creates `.venv`, installs the package with dev extras, and installs the skill bundle. | Update when local setup steps change. Keep it consistent with installation docs. |
| `uninstall.sh` | Convenience uninstall script. | Uninstalls the package from `.venv` and uv tool installs, then tells the user to remove local environment state. | Update when uninstall steps change. |
| `sitecustomize.py` | Subprocess coverage hook. | Starts coverage in Python subprocesses when `COVERAGE_PROCESS_START` is set, letting integration tests include CLI subprocess coverage. | Edit only if subprocess coverage behavior changes. |

## Root directories

| Directory | Purpose | What it contains | When to edit |
| --- | --- | --- | --- |
| `social_research_probe/` | Application package. | CLI, commands, platform adapters, services, technologies, config, skill files, and utilities. | Edit for product behavior. See [Module Reference](module-reference.md). |
| `tests/` | Test suite. | Unit, integration, contract, and eval tests plus fixtures. | Edit alongside behavior changes or docs contract changes. |
| `docs/` | Human documentation. | Markdown guides, Mermaid diagram sources, rendered SVGs, and sample images. | Edit when behavior or explanations change. Do not edit `docs/installation.md` unless explicitly requested. |
| `scripts/` | Developer/release helper scripts. | Release tagging script and script cache artifacts if generated locally. | Edit for automation helpers that are not part of the user-facing CLI. |
| `.github/` | GitHub automation. | CI and release workflows. | Edit when test matrix, lint steps, build, release, or PyPI publishing workflow changes. |

## Generated or local-only root items

These may appear in a working tree but should not be treated as source files:

| Path | Meaning | What to do |
| --- | --- | --- |
| `.coverage` and `.coverage.*` | Coverage data from test runs. | Do not edit. Regenerated by tests and ignored by git. |
| `.venv/` | Local Python virtual environment. | Do not commit. Recreate when dependencies or Python version change. |
| `.pytest_cache/` | Pytest cache. | Safe to delete. |
| `.ruff_cache/` | Ruff lint cache. | Safe to delete. |
| `.hypothesis/` | Hypothesis test case database. | Safe to delete unless debugging property-test failures. |
| `__pycache__/` | Python bytecode cache. | Safe to delete. |
| `.claude/` | Local Claude/Codex workspace settings. | Local-only. Do not rely on it for project behavior. |
| `.git/` | Git repository metadata. | Managed by git. Do not edit manually. |

## How the root files work together

Packaging starts with `pyproject.toml`. It names the package, declares
dependencies, exposes the `srp` console script, and tells Hatch to read the
version from `VERSION`.

Development workflows use `pyproject.toml`, `requirements-dev.txt`, `Makefile`,
and the GitHub CI workflow. Local commands can run through the Makefile, while
CI runs Ruff and pytest across the supported Python matrix.

User configuration examples live in `config.toml.example` and `.env.example`.
The real user config and secrets should live in the active data directory, not
in the repository root.

Release automation is tied to `VERSION`, `scripts/tag_release.sh`, and
`.github/workflows/release.yml`. Pushing a `VERSION` change to `main` triggers
release packaging, GitHub release creation, and PyPI publishing.

Documentation starts at `README.md`, then routes to `docs/README.md`. The docs
hub links to task-specific pages such as architecture, commands, scoring,
statistics, charts, Python language guidance, and platform extension.

## Safe editing rules

| If you are changing... | Also check... |
| --- | --- |
| Runtime dependencies | `pyproject.toml`, `requirements.txt`, `uv.lock`, [Runtime Dependencies](runtime-dependencies.md). |
| Dev/test dependencies | `pyproject.toml`, `requirements-dev.txt`, `uv.lock`, CI workflow. |
| Config keys | `config.toml.example`, `.env.example` if env vars are involved, [Configuration](configuration.md), tests. |
| CLI commands | `README.md`, [Usage](usage.md), [Commands](commands.md), command tests. |
| Release process | `VERSION`, `scripts/tag_release.sh`, `.github/workflows/release.yml`, `CHANGELOG.md`. |
| Documentation structure | `docs/README.md`, docs contract tests, diagram references. |
| Generated outputs | `.gitignore` if the files should not be committed. |

When in doubt, do not put user data, real secrets, cache contents, reports, or
local environment files in the repository root. Use the configured data
directory for runtime state.
