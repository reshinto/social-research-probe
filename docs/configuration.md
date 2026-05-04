[Back to docs index](README.md)


# Configuration

`config.py` owns non-secret runtime configuration. It starts from `DEFAULT_CONFIG`, merges `config.toml` from the active data directory when present, and exposes typed accessors through `Config`.

![Configuration lifecycle](diagrams/config_lifecycle.svg)

## Main Sections

| Section | Source use |
| --- | --- |
| `[llm]` | Selects `none`, `claude`, `gemini`, `codex`, or `local`; stores timeout and runner flags. |
| `[corroboration]` | Selects provider and max claim budgets. |
| `[platforms.youtube]` | YouTube limits, comments, claims, narratives, export options. |
| `[scoring.weights]` | Optional global trust/trend/opportunity weights. |
| `[stages.youtube]` | Highest-level stage gates. |
| `[services]` | Service-level gates read by `BaseService.is_enabled()`. |
| `[technologies]` | Flat technology gates read by `BaseTechnology.execute()`. |
| `[tunables]` | Summary divergence threshold and per-item summary word target. |
| `[debug]` | Technology log control. |
| `[voicebox]` | HTML narration and playback settings. |
| `[database]` | SQLite path and text-persistence settings. |

## Stage Gates

Current YouTube stage gates are:

```text
fetch, classify, score, transcript, summary, corroborate, stats, charts,
synthesis, assemble, structured_synthesis, report, narration, comments,
claims, narratives, export, persist
```

If a stage gate is false, the stage skips before service or technology work.

## Service Gates

Service classes declare dotted `enabled_config_key` values such as `services.youtube.reporting.html`. The current compatibility lookup checks the final leaf name against known service names. Unknown service names are disabled by default.

| Section | Controls |
| --- | --- |
| `[llm]` | Runner name, timeout, and runner-specific CLI settings. |
| `[corroboration]` | Provider selection and claim caps. |
| `[platforms.youtube]` | Search result count, recency, top-N enrichment, cache TTLs. |
| `[scoring.weights]` | Optional trust/trend/opportunity weight overrides. |
| `[stages.youtube]` | Stage-level gates. |
| `[services.youtube.*]` | Service-level gates (e.g. `classifying.provider`, `corroborating`). |
| `[technologies]` | Provider and adapter gates (e.g. `classifying`, `tavily`, `exa`). |
| `[tunables]` | Summary divergence and summary word limits. |
| `[voicebox]` | Optional narration defaults. |
| `[debug]` | Debug gates (e.g. `technology_logs_enabled`). |
| `[database]` | SQLite path and persistence controls used by research runs, watches, and alerts. |
| `[notifications]` | Local watch-alert notification channels and defaults. |
| `[schedule]` | Defaults for printed local scheduling helper commands. |

## Gates

A stage runs only if its stage gate allows it. A service or technology also checks its own gate. This gives three levels of control: pipeline step, service family, and concrete provider.

```bash
srp config set llm.runner gemini
srp config set platforms.youtube.enrich_top_n 3
srp config set technologies.tavily false
```

Technology gates are flat names under `[technologies]`, for example `youtube_search`, `llm_ensemble`, `corroboration_host`, `export_package`, and `sqlite_persist`. Unknown technology names are disabled.

`srp watch run` requires SQLite persistence. It fails clearly if `database.enabled=false`, `services.persistence.sqlite=false`, `technologies.sqlite_persist=false`, or the platform persist stage is disabled. Watch tests should monkeypatch the research runner and use temporary data directories; they should not make network calls.

`srp watch run --notify` and `srp watch run-due --notify` send notifications only for newly created alert events. `notifications.enabled=false` disables sending globally. Channel-specific `enabled=false` disables that channel even when it is requested explicitly. Notification delivery attempts are recorded locally in SQLite when possible, but delivery failures do not fail the watch run.

`srp schedule cron` and `srp schedule launchd` print local helper configuration only. They include the active `--data-dir` in generated commands and do not install cron entries, load launchd jobs, or start a daemon.

## Secrets

`commands/config.py` maps logical secret names to environment variables by uppercasing and prefixing `SRP_`.

| Logical name | Environment variable |
| --- | --- |
| `youtube_api_key` | `SRP_YOUTUBE_API_KEY` |
| `exa_api_key` | `SRP_EXA_API_KEY` |
| `brave_api_key` | `SRP_BRAVE_API_KEY` |
| `tavily_api_key` | `SRP_TAVILY_API_KEY` |

Secret file values live in `[secrets]` in `secrets.toml`. Environment variables win over file values.
