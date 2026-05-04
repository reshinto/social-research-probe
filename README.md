# social-research-probe

[![CI](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml/badge.svg)](https://github.com/reshinto/social-research-probe/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/social-research-probe)](https://pypi.org/project/social-research-probe/)
[![Python >=3.11](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](https://pypi.org/project/social-research-probe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/reshinto/social-research-probe/blob/main/LICENSE)

`social-research-probe` installs the `srp` command. The command builds an evidence packet from a social-media research question: it fetches source items, ranks them, enriches the strongest sources, extracts claims, corroborates those claims when providers are configured, clusters narratives, renders reports, exports data files, and can persist the run to SQLite.

The source code currently registers two platform keys:

| Key       | Meaning                                                                      |
| --------- | ---------------------------------------------------------------------------- |
| `youtube` | The concrete YouTube pipeline in `social_research_probe/platforms/youtube`.  |
| `all`     | A meta-pipeline that runs every concrete pipeline; today that means YouTube. |

## Quickstart

```bash
srp setup
srp config set-secret youtube_api_key
srp research youtube "AI agents" "latest-news,trends"
```

For a no-network verification run:

```bash
srp --data-dir /tmp/srp-demo demo-report
```

`demo-report` writes a synthetic HTML report, export files, and `srp.db` under the selected data directory.

## Runtime Flow

![Research data flow](docs/diagrams/data-flow.svg)

A YouTube run follows the stage order defined by `YouTubePipeline.stages()`:

1. `fetch`: search YouTube, hydrate metadata, and compute engagement metrics.
2. `classify`: assign `primary`, `secondary`, `commentary`, or `unknown` source classes.
3. `score`: compute trust, trend, opportunity, and overall scores.
4. `transcript`, `stats`, `charts`: run concurrently after scoring.
5. `comments`: fetch top-level comments for top-ranked videos.
6. `summary`: build text surrogates and summarize top-ranked items.
7. `claims`: extract structured claims from primary text.
8. `corroborate`: check extracted claims with configured providers.
9. `narratives`: cluster related claims into narrative groups.
10. `synthesis`: produce the research synthesis.
11. `assemble`: build the report dictionary.
12. `structured_synthesis`: attach structured report sections if available.
13. `report` and `narration`: render HTML and optional audio in parallel.
14. `export`: write CSV, Markdown, and JSON artifacts.
15. `persist`: write the run to SQLite.

## Main Commands

```bash
srp research [platform] TOPIC PURPOSES
srp research [platform] "natural language query"
srp config show
srp config path
srp config set KEY VALUE
srp config set-secret NAME
srp db init
srp db stats
srp claims list --needs-review
srp serve-report --report PATH_TO_HTML
```

The command parser accepts the platform as the first `research` argument only when it matches a registered pipeline key. If it is omitted, the parser uses `all`.

## Documentation

Start with [docs/README.md](docs/README.md). The docs were written from the source tree: CLI parser, config defaults, pipeline stages, service and technology base classes, persistence schema, export package, tests, and skill bundle.

## Architecture In One Paragraph

`cli/parsers.py` builds the command surface, `cli/handlers.py` dispatches parsed commands into `commands/*`, and `commands/research.py` builds a `ParsedRunResearch`. The orchestrator creates `PipelineState` and runs a registered platform pipeline. Platform stages decide order and state keys. Services own batch execution and normalization. Technologies own concrete provider calls, local algorithms, renderers, and persistence adapters. Utilities hold shared types, cache, config, state, display, claims, narratives, report, and IO helpers.

## License

MIT. See [LICENSE](LICENSE).
