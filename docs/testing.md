[Back to docs index](README.md)

# Testing

![Testing pyramid](diagrams/testing-pyramid.svg)

The repository uses unit, integration, contract, and eval tests. Each test type protects a different risk: pure logic bugs, pipeline wiring bugs, documentation drift, and model-output quality.

When changing code, choose the smallest test that can prove the behavior. When changing docs, run the docs contract tests so links and rendered diagram sources stay aligned.

## Test types

| Type | Location | Purpose |
| --- | --- | --- |
| Unit | `tests/unit` | Pure functions, command helpers, services, adapters. |
| Integration | `tests/integration` | Pipeline, CLI state, packet output, runner health. |
| Contract | `tests/contract` | Docs navigation, diagrams, package/version guardrails. |
| Evals | `tests/evals` | LLM and summary quality checks. |

## Commands

```bash
pytest
pytest tests/unit/test_utils_pipeline_cache.py
pytest tests/contract/test_docs_navigation.py tests/contract/test_docs_diagrams.py
ruff check .
```

Coverage is configured in `pyproject.toml` with a 100 percent gate for the package. When changing docs, run the docs contract tests at minimum.

![Fake seam for integration tests](diagrams/dp_fake_seam.svg)

## How to decide what to run

| Change | Minimum useful check |
| --- | --- |
| Markdown docs only | `pytest --no-cov tests/contract/test_docs_navigation.py tests/contract/test_docs_diagrams.py` |
| Config or cache behavior | Relevant unit tests plus one integration path using a temporary data directory. |
| CLI parser or command output | Command unit tests and at least one subprocess-style integration test if output shape changes. |
| Platform fetch or normalization | Fake platform tests first, then provider-specific tests only when credentials are intentionally available. |
| LLM prompt or synthesis contract | Unit tests for packet shape plus eval or harness runs when output quality matters. |

The fake platform seam exists so integration tests can exercise the pipeline without network calls. Prefer fakes for deterministic behavior. Use live provider tests sparingly because they are slower, cost money, and can fail for reasons unrelated to code.
