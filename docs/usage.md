[Back to docs index](README.md)


# Usage

The command parser builds this general shape:

```bash
srp [--data-dir PATH] [--verbose] [--version] COMMAND ...
```

## Research Inputs

`commands/research.py` accepts two research forms:

```bash
srp research [PLATFORM] TOPIC PURPOSES
srp research [PLATFORM] "NATURAL LANGUAGE QUERY"
```

`PLATFORM` is recognized only if the first positional argument matches a key in `PIPELINES`. Current keys are `youtube` and `all`. If no platform is given, the parser sets `platform = "all"`.

`PURPOSES` is comma-separated:

```bash
srp research youtube "AI coding agents" "latest-news,trends"
```

When only one argument remains after platform parsing, the code treats it as a natural-language query and calls the query classifier to produce a topic and purpose name.

## Useful Flags

| Flag | Code effect |
| --- | --- |
| `--no-shorts` | Sets platform override `include_shorts = False`. |
| `--no-transcripts` | Sets `fetch_transcripts = False`. |
| `--no-html` | Sets `allow_html = False`. |
| `--data-dir PATH` | Resolves config, secrets, cache, reports, exports, and SQLite under that path. |

## Reading Outputs

A successful research command prints the report path or a `srp serve-report --report ...` command. Export paths are attached to the report dictionary by `export_stage.py` and written beside the HTML report under `reports/`.

Use these commands after a run:

```bash
srp db stats
srp claims list --limit 20
srp claims stats --output json
srp serve-report --report PATH_TO_HTML
```

## Workflow

1. Pick a data directory for the project or let srp use the default.
2. Configure the YouTube key and optional runner/provider keys.
3. Add or choose purpose names.
4. Run research.
5. Inspect the HTML report, CSV exports, claims, and database rows.
6. If an output is missing, check config gates and technology availability before changing code.
