[Back to docs index](README.md)


# Commands

![Command surface](diagrams/command-surface.svg)

The command list comes from `Command` in `commands/__init__.py` and parser registration in `cli/parsers.py`.

## Global Flags

| Flag | Meaning |
| --- | --- |
| `--data-dir PATH` | Resolve and set `SRP_DATA_DIR` before command dispatch. |
| `--verbose` | Parsed and passed through the top-level namespace. |
| `--version` | Print package version and path, then exit. |

## Research And Reports

```bash
srp research [platform] TOPIC PURPOSES [--no-shorts] [--no-transcripts] [--no-html]
srp corroborate-claims --input claims.json [--providers llm_search,exa,brave,tavily] [--output out.json]
srp render --packet packet.json [--output-dir charts]
srp report --packet packet.json [--compiled-synthesis file] [--opportunity-analysis file] [--final-summary file] [--out report.html]
srp serve-report --report report.html [--host 127.0.0.1] [--port 8000] [--voicebox-base URL]
srp demo-report
```

`render` is for chart/stat output from a saved packet. `report` re-renders HTML from a packet. `serve-report` starts a local HTTP server and Voicebox proxy for an existing HTML report.

## Config

```bash
srp config show [--output text|json|markdown]
srp config path [--output text|json|markdown]
srp config set KEY VALUE [--output text|json|markdown]
srp config set-secret NAME [--from-stdin] [--output text|json|markdown]
srp config unset-secret NAME [--output text|json|markdown]
srp config check-secrets [--needed-for research] [--platform youtube] [--corroboration exa|brave|tavily] [--output text|json|markdown]
```

Regular config values go to `config.toml`. Secrets go to `secrets.toml` or environment variables.

## State Commands

The parser also registers state-management commands. Some have no help text in the root help output, but they are valid commands.

```bash
srp show-topics [--output text|json|markdown]
srp update-topics --add TOPIC... [--output text|json|markdown]
srp update-topics --remove TOPIC... [--force]
srp update-topics --rename OLD NEW

srp show-purposes [--output text|json|markdown]
srp update-purposes --add PURPOSE... [--output text|json|markdown]
srp update-purposes --remove PURPOSE... [--force]
srp update-purposes --rename OLD NEW

srp suggest-topics [--count N] [--output text|json|markdown]
srp suggest-purposes [--count N] [--output text|json|markdown]
srp stage-suggestions [--from-stdin] [--output text|json|markdown]
srp show-pending [--output text|json|markdown]
srp apply-pending [--topics IDS] [--purposes IDS] [--output text|json|markdown]
srp discard-pending [--topics IDS] [--purposes IDS] [--output text|json|markdown]
```

The state files use JSON schemas and migration helpers in `utils/state`.

## Database And Claims

```bash
srp db path
srp db init
srp db stats

srp claims list [--run-id ID] [--topic TEXT] [--claim-type TYPE] [--needs-review] [--needs-corroboration] [--corroboration-status STATUS] [--extraction-method METHOD] [--limit N] [--output text|json|markdown]
srp claims show CLAIM_ID [--output text|json|markdown]
srp claims stats [--output text|json|markdown]
srp claims review CLAIM_ID --status verified|rejected|disputed|ignored|unreviewed [--importance low|medium|high|critical] [--notes TEXT] [--output text|json|markdown]
srp claims note CLAIM_ID TEXT [--output text|json|markdown]
```

Claims commands query SQLite through `technologies/persistence/sqlite/queries.py`.
