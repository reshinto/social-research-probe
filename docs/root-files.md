[Back to docs index](README.md)


# Root Files

The repository root mixes package metadata, install helpers, project policy files, and generated local artifacts.

## Source-Controlled Files

| File | Purpose |
| --- | --- |
| `pyproject.toml` | Package metadata, dependencies, script entry point, test and Ruff config. |
| `uv.lock` | Locked environment data for uv users. |
| `requirements.txt` | Runtime dependency list for pip-style installs. |
| `requirements-dev.txt` | Development dependency list. |
| `config.toml.example` | Example runtime configuration shipped in the wheel. |
| `.env.example` | Environment variable reference. |
| `Makefile` | Convenience command entry points. |
| `runtests.sh` | Test wrapper. |
| `install.sh`, `uninstall.sh` | Local install helpers. |
| `VERSION` | Hatch version source. |
| `CHANGELOG.md` | Release history. |
| `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` | Project policy files. |
| `sitecustomize.py` | Local import/runtime customization. |

## Directories

| Directory | Purpose |
| --- | --- |
| `social_research_probe/` | Python package. |
| `tests/` | Test suite and fixtures. |
| `docs/` | Documentation and rendered SVG diagrams. |
| `scripts/` | Release helper scripts. |
| `.github/` | GitHub workflows and metadata. |
| `.githooks/` | Local git hook helpers. |
| `.claude/` | Local assistant-related project metadata. |

Generated directories such as `.venv`, `.pytest_cache`, `.ruff_cache`, `.hypothesis`, `htmlcov`, and coverage files are local artifacts and should not be treated as source behavior.
