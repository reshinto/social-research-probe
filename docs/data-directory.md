[Back to docs index](README.md)

# Data Directory

![Data and cache layout](diagrams/cache-layout.svg)

The data directory is the local home for config, secrets, state, cache, charts, and reports. Resolve it with `srp config path` or set it with `--data-dir`.

Understanding this directory is important because the project is local-first. Most behavior that feels "persistent" is stored here: saved topics, saved purposes, cached provider outputs, rendered charts, and generated reports.

## Files and folders

| Path | Purpose |
| --- | --- |
| `config.toml` | Non-secret user configuration. |
| `secrets.toml` | Secret values, written with `0600` permissions. |
| `topics.json` | Saved topic names. |
| `purposes.json` | Saved purpose definitions. |
| `pending_suggestions.json` | Staged topic and purpose suggestions. |
| `cache/transcripts` | Transcript cache. |
| `cache/whisper` | Whisper fallback cache. |
| `cache/summaries` | LLM summary cache. |
| `cache/corroboration` | Provider evidence cache. |
| `cache/classification` | Query classification cache. |
| `cache/stages/*` | Stage-level cached outputs. |
| `charts/*.png` | Rendered chart PNGs. |
| `report.md` and `reports/*.html` | Report outputs. |

## Best practice

Use a project-local `.skill-data` for experiments you want to keep with a workspace. Use the default home directory for personal long-lived settings.

Do not commit the data directory unless you intentionally want to publish its contents. It can contain research topics, cached transcripts, summaries, external evidence, and generated reports. For open-source examples, prefer small hand-written fixtures instead of real cache output.

## When to delete data

Delete cache entries when you need a fresh provider response or when a cached output was created with a bad configuration. Delete generated reports when they contain sensitive research. Keep `config.toml`, `topics.json`, and `purposes.json` if you want to preserve your workflow settings.

If behavior differs between two machines, compare `srp config path`, `config.toml`, `secrets.toml`, and environment variables first. Most "it works here but not there" issues come from a different data directory or missing provider secret.

## Example layouts

Personal default:

```text
~/.social-research-probe/
  config.toml
  secrets.toml
  topics.json
  purposes.json
  cache/
  charts/
  reports/
```

Project-local experiment:

```text
my-research-project/
  .skill-data/
    config.toml
    topics.json
    purposes.json
    cache/
    charts/
    reports/
```

Use the project-local layout when the research context should stay with a workspace. Use the home layout when you want one personal setup reused across many topics.
