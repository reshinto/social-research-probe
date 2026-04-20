# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-20

### Added
- Async hot path: all API calls, corroboration, and LLM ensemble now run concurrently via `asyncio` and `httpx`
- Multi-LLM transcript summarisation: Claude + Gemini + Codex fan-out with first-success fallback
- Whisper transcript fallback when YouTube captions unavailable
- Natural-language query mode: `srp research "what's trending in AI safety?"` auto-classifies topic/purpose
- HTML report output with embedded charts and TTS-ready section headings
- Auto-corroboration of top-5 items via Exa, Brave, or Tavily on every research run
- `VERSION` file as single source of truth for package version (hatchling dynamic versioning)
- Release workflow: `VERSION` push to main → GitHub release → PyPI publish via OIDC
- ./.venv/bin/python 3.13 added to CI test matrix
- MIT `LICENSE` file
- This `CHANGELOG.md`

### Changed
- `pipeline.py` (757L) split into `pipeline/` package: scoring, enrichment, stats, charts, corroboration, svs, orchestrator
- `cli.py` (611L) split into `cli/` package: parsers, handlers, utils, `__init__`
- `synthesize/formatter.py` split into `synthesize/explanations/` package with per-model explanation modules
- `corroboration` backends migrated from `urllib` to `httpx.AsyncClient`
- `llm/ensemble.py` migrated from `ThreadPoolExecutor` to `asyncio.create_subprocess_exec`
- `YouTubeAdapter.enrich()` converted to native `async def`
- All broad exception handlers narrowed; `asyncio.TimeoutError` replaced with built-in `TimeoutError`

### Fixed
- Nested `asyncio.run()` inside `asyncio.to_thread()` when adapter called `run_coro()`
- Late-binding closure bug in pipeline `asyncio.to_thread` lambda
- `strict=True` added to `zip()` in LLM ensemble response collection

## [0.1.0] - 2026-04-19

### Added
- Initial release: `srp research`, `srp update-topics`, `srp update-purposes`, corroboration backends, stats suite, chart rendering, Claude Code skill integration

[Unreleased]: https://github.com/user/social-research-probe/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/user/social-research-probe/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/user/social-research-probe/releases/tag/v0.1.0
