# Contributing

Thank you for taking the time to contribute!

## Prerequisites

- Python 3.11+
- A virtual environment: `python -m venv .venv && source .venv/bin/activate`
- Dev dependencies: `pip install -e '.[dev]'`

## Development workflow

1. Fork the repo and create a branch: `git switch -c feat/your-feature`
2. Write a failing test first (TDD — see below)
3. Implement the minimum code to pass the test
4. Run `pytest --cov-fail-under=100 --cov-branch -q` — must be green
5. Run `ruff check social_research_probe tests` + `ruff format --check .`
6. Open a pull request against `main`

## Test-driven development

Every new behaviour must have a failing test before implementation. No exceptions:

```bash
pytest tests/unit/test_mymodule.py -x -q   # watch it fail
# implement
pytest tests/unit/test_mymodule.py -x -q   # watch it pass
pytest --cov-fail-under=100 --cov-branch   # full suite must stay green
```

## File size limits

- **500 lines max** per file. Split into sub-packages before reaching the limit.
- **50 lines max** per function. Extract helpers when functions grow.

## Versioning and releases

Releases are driven by the `VERSION` file in the repo root:

1. Update `VERSION` (e.g. `0.2.1`)
2. Add a section to `CHANGELOG.md`
3. Merge to `main` — the `release.yml` workflow creates the tag, GitHub release, and PyPI publish automatically

PyPI publishing uses OIDC trusted-publishing. You must configure the `pypi` environment in GitHub repository settings before the first publish.

## Code style

- `ruff` for linting and formatting (`line-length = 100`)
- No `# noqa`, `# type: ignore`, or `# pragma: no cover` — fix issues properly
- No section-header comments; let function names document structure

## Security

See [SECURITY.md](SECURITY.md) for responsible disclosure.
