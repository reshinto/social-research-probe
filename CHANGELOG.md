# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.8] - Unreleased

Derived from `git log v0.0.7..HEAD` through `4cfd9c7`, plus the current documentation updates in this working tree.

### Refactored (refactor/analyzing-services)

- Consolidated `BaseService` from `services/base.py` into `services/__init__.py` and `BaseTechnology` from `technologies/base.py` into `technologies/__init__.py`, eliminating unnecessary base files.
- Consolidated `platforms/base.py` into `platforms/__init__.py`.
- Consolidated analyzing helpers, corroborating submodules, reporting writer, and scoring compute/weights into their respective package `__init__` files.
- Restructured synthesizing service into a `synthesis/` subfolder with helpers.
- Restructured LLM service into a `core/` subfolder following the `BaseService` pattern.
- Refactored YouTube sourcing as a `BaseService` with sequential technology steps.
- Moved all `BaseTechnology` subclasses out of `services/` into `technologies/`, enforcing the encapsulation boundary.
- Moved YouTube helper functions (`search_youtube`, `hydrate_youtube`, and engagement helpers) from `services/sourcing/youtube.py` into `technologies/web_search`.
- Consolidated `StatResult` from `statistics/base.py` into `statistics/__init__.py`.
- Consolidated `ChartResult` from `charts/base.py` and `write_placeholder_png` from `charts/_png_writer.py` into `charts/__init__.py`.
- Consolidated `CorroborationResult`, `CorroborationProvider`, and all filter utilities (`filter_results`, `is_video_url`, `is_self_source`, `VIDEO_HOST_DOMAINS`) from `corroborates/base.py` and `corroborates/_filters.py` into `corroborates/__init__.py`.

### Added

- Added the modular `services/` layer for analyzing, scoring, enriching, corroborating, synthesizing, sourcing, and reporting responsibilities.
- Added the modular `technologies/` layer for atomic implementations such as chart renderers, corroboration providers, LLM CLIs, media fetchers, statistics modules, transcript fetchers, TTS, validation, and web-search wrappers.
- Added platform-specific research orchestration under `platforms/`, including `PipelineState`, the `all` meta-platform, and the concrete YouTube pipeline.
- Added persistent chart output support so chart PNGs are written under the active data directory instead of a temporary directory.
- Added `serve-report`, report re-rendering, Voicebox profile discovery, and Voicebox audio report support.
- Added prompt/result caching and timing/cache visibility logs for natural-language query classification.
- Added centralized progress, fast-mode, service-log, cache, secret, CLI parsing, and core utility modules.
- Added dedicated command modules for topics, purposes, suggestions, pending suggestions, config, rendering, reports, setup, skill install, and claim corroboration.
- Added `config.toml.example` coverage for current platform, stage, service, technology, LLM, corroboration, tunable, debug, and Voicebox settings.
- Added a dedicated `docs/scoring.md` guide that explains trust, trend, opportunity, overall score calculation, weight overrides, missing-data behavior, and how to interpret ranked results.
- Added a `docs/root-files.md` guide explaining the purpose and edit rules for repository root files and support directories.
- Added Claude Code `/srp` skill usage to `docs/commands.md` and consolidated duplicate command examples out of the usage docs.
- Added documentation visuals for scoring, including a formula overview, axis-balance view, and weighted-sum worked example.
- Added sample statistics visuals for every automatic statistic and every available advanced statistics module in `docs/statistics.md`.
- Added embedded chart images to `docs/charts.md` so each chart explanation loads the relevant sample PNG.
- Added a more visual architecture landscape diagram to `docs/architecture.md`.
- Added concrete code examples to `docs/adding-a-platform.md` for a new platform client, pipeline, config defaults, CLI usage, and fake-client tests.
- Added corroboration input/output examples, verdict interpretation visuals, and troubleshooting guidance to `docs/corroboration.md`.
- Expanded `docs/data-directory.md` with `~/.social-research-probe` storage layout, lookup commands, missing charts/reports/cache/config/secrets guidance, and a local data map diagram.
- Added `docs/api-costs-and-keys.md` to explain free/local paths, quota-based APIs, paid provider APIs, Claude/Gemini/Codex runner authentication, and how LLM usage can spend money.
- Added an API cost map SVG showing which paths are local, quota-based, API-key backed, or runner-account billed.

### Changed

- Migrated the codebase from the older root-level `pipeline/`, `llm/`, `corroboration/`, `stats/`, `viz/`, `render/`, `validation/`, and `synthesize/` layout into explicit `services/`, `technologies/`, `platforms/`, and `utils/` boundaries.
- Renamed user-facing and internal terminology from `backend` to `provider` and from `packet` to `report` where the code now models provider selection and report assembly.
- Reworked research execution so command parsing routes into `platforms.orchestrator.run_pipeline()` and platform-specific stages own stage order.
- Reworked the CLI parser and handler layer around command enums, config subcommands, special commands, and smaller command files.
- Centralized LLM runner registration, runner fallback, prompts, schemas, and agentic-search citation/result types.
- Moved YouTube sourcing into `services.sourcing.youtube` and YouTube API / `yt-dlp` behavior into `technologies.media_fetch`.
- Moved chart rendering and statistical analysis into service and technology modules with dataset-keyed caching.
- Refreshed Claude skill references to match the current command, config, pending suggestion, topic, purpose, and research behavior.
- Rewrote the documentation set to be more beginner-friendly and platform-agnostic, with YouTube documented as the first implemented adapter rather than the project purpose.
- Expanded `docs/python-language-guide.md` into a full project-specific Python primer covering syntax, data structures, typing, dataclasses, classes, async/await, subprocesses, files, JSON/TOML, caching, pytest, fakes, and repository patterns.
- Expanded `docs/statistics.md` with interpretation guidance, examples, and diagrams for report statistics and advanced statistical modules.
- Expanded `docs/commands.md` with example inputs and expected output shapes for CLI commands.
- Expanded `docs/charts.md` with chart-specific interpretation guidance and corrected chart image filename references.
- Expanded architecture, design-pattern, configuration, corroboration, cost, data-directory, security, synthesis, testing, runtime-dependency, model-applicability, module-reference, usage, and platform-extension documentation with more context, tradeoffs, and practical guidance.
- Updated diagram styling across generated SVGs to use white canvases with meaningful colored nodes for dark-mode readability.
- Updated `config.toml.example` and `.env.example` so every active setting has a comment and stale runner model examples are removed.
- Updated `docs/scoring.md` scored-item field table to reflect nested `scores.*` structure (`scores.trust`, `scores.trend`, `scores.opportunity`, `scores.overall`) and added `source_class` field.
- Updated `docs/charts.md` and `docs/statistics.md` to reference `scores.*` fields instead of flat field names.
- Updated `docs/python-language-guide.md` example dict and sorting lambda to use nested `scores` structure.
- Updated `docs/how-it-works.md` to add the classify stage (step 4) and mental model table row between fetch and score.
- Updated `docs/diagrams/src/data-flow.mmd` to add Classify node between Fetch and Score; regenerated `data-flow.svg`.

### Fixed

- Fixed corroboration provider registration and removed stale coupling to the old `BaseTechnology` shape.
- Fixed pipeline logging, error handling, and cache behavior after the modular architecture migration.
- Fixed modular reporting service config so HTML/audio report gates map to the current config schema.
- Fixed chart generation so report chart PNGs persist under `data_dir/charts/`.
- Fixed broken import paths after package reorganization.
- Fixed `install-skill` setup by defaulting the Voicebox server URL secret when needed.
- Fixed unit-test and package-version issues found during the post-release refactor.
- Fixed research CLI ambiguity by requiring or resolving platform arguments through the current parser rules.
- Fixed stale `.env.example` corroboration wording that still referred to backend selection and outdated Brave pricing assumptions.
- Fixed test suite `PermissionError`s on macOS by mocking HTTP server binds and restricting file writes inside `~/.claude` during local test sandbox execution.
- Fixed `YouTubeSourcingService.execute_one()` to gate on service-level feature flag; updated `enabled_config_key` to use correct config leaf name.

### Removed

- Removed dead render stubs, deleted markdown render leftovers, and removed unused render/TTS HTTP modules.
- Removed obsolete root validation, root stats, root viz, old pipeline, old LLM, and old corroboration package entry points after their responsibilities moved into modular packages.
- Removed unused platform adapter/listing helpers that were replaced by the current registry shape.

### Tests

- Reworked the test suite around the new module boundaries and achieved full coverage for the modular architecture pass.
- Added or refreshed coverage for CLI handlers, config commands, platform orchestration, YouTube sourcing, services, technologies, report rendering, Voicebox, LLM runners, caching, and utility modules.
- Ran lint and format fixes across modules and tests after the refactor.

## [0.0.7] - 2026-04-21

### Added

- Added the evidence and reliability suite with golden fixtures for scoring, statistics, corroboration, fetch/signal/trust behavior, enrichment, synthesis, validation, visualization, reporting, LLM runners, and drift/mutation checks.
- Added a multi-sample judge-LLM reliability harness with variance gates.
- Added summary quality evaluation for key-phrase and word-limit behavior.
- Added rendered white-background documentation diagrams for corroboration, runner-agnostic search, and reliability flows.

### Changed

- Routed agentic search corroboration through the LLM runner abstraction.
- Renamed Gemini search behavior toward the `llm_search` provider model.
- Moved the evidence suite under unit tests and renamed phase-numbered tests to descriptive names.
- Documented the evidence suite, eval scripts, runtime dependencies, storage reference, and LLM-runner-first search model.

### Fixed

- Excluded self-source and video-hosting domains from corroboration evidence.
- Fixed misleading testing documentation around coverage subset commands and evidence test framing.

## [0.0.6] - 2026-04-21

### Added

- Added Gemini search corroboration and merged 100-word summary support.
- Added synthesis-fidelity improvements that close the gap between transcript summaries and final synthesis.

### Changed

- Refreshed stale architecture diagrams to match the then-current registries.
- Overhauled objective, cost-optimization, config lifecycle, and design-pattern documentation.

### Fixed

- Covered CI-only enrichment branches and collapsed duplicated pytest steps.

## [0.0.5] - 2026-04-21

### Added

- Added the first tagged release for the synthesis-fidelity and Gemini-search work that later also appeared as `0.0.6`.

### Changed

- Enabled version detection to avoid unnecessary release publishing.

## [0.0.3] - 2026-04-20

### Fixed

- Updated the release workflow.

## [0.0.2] - 2026-04-20

### Fixed

- Fixed the `install-skill` command.

## [0.0.1] - 2026-04-20

### Added

- Async hot path: all API calls, corroboration, and LLM ensemble now run concurrently via `asyncio` and `httpx`
- Multi-LLM transcript summarisation: Claude + Gemini + Codex fan-out with first-success fallback
- Whisper transcript fallback when YouTube captions unavailable
- Natural-language query mode: `srp research "what's trending in AI safety?"` auto-classifies topic/purpose
- HTML report output with embedded charts and TTS-ready section headings
- Auto-corroboration of top-N items via Exa, Brave, or Tavily on every research run
- `VERSION` file as single source of truth for package version (hatchling dynamic versioning)
- Release workflow: `VERSION` push to main → GitHub release → PyPI publish via OIDC
- Python 3.13 added to CI test matrix
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

[0.0.8]: https://github.com/reshinto/social-research-probe/compare/v0.0.7...HEAD
[0.0.7]: https://github.com/reshinto/social-research-probe/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/reshinto/social-research-probe/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/reshinto/social-research-probe/compare/v0.0.3...v0.0.5
[0.0.3]: https://github.com/reshinto/social-research-probe/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/reshinto/social-research-probe/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/reshinto/social-research-probe/releases/tag/v0.0.1
