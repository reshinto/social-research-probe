[Back to docs index](README.md)


# Testing

![Testing pyramid](diagrams/testing-pyramid.svg)

`pyproject.toml` configures pytest with coverage on `social_research_probe`, branch coverage, and `--cov-fail-under=100` by default.

## Main Commands

```bash
.venv/bin/python -m pytest
.venv/bin/python -m pytest --no-cov tests/contract/test_docs_navigation.py tests/contract/test_docs_diagrams.py tests/contract/test_skill_bundle.py
.venv/bin/python -m pytest --no-cov tests/unit/test_pipeline_yt.py
.venv/bin/python -m pytest --no-cov tests/integration/test_research_e2e.py
```

## Test Areas

| Directory | Purpose |
| --- | --- |
| `tests/unit` | Pure helpers, commands, services, technologies, SQLite, rendering. |
| `tests/integration` | End-to-end behavior across layers. |
| `tests/contract` | Repository rules: docs links, diagrams, skill bundle, type/length/static-method restrictions. |
| `tests/evals` | LLM and claim quality checks. |
| `tests/fixtures` | Fake YouTube, fake corroboration, golden data. |

## Docs Contracts

Every direct `docs/*.md` file must be linked from `docs/README.md`, every non-hub doc must contain a breadcrumb to `README.md`, all internal links must resolve, every SVG must be referenced, and every Mermaid source must have a matching SVG.
