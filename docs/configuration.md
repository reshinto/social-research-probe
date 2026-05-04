[Back to docs index](README.md)

# Configuration

![Configuration lifecycle](diagrams/config_lifecycle.svg)

Configuration is loaded from `DEFAULT_CONFIG` in `social_research_probe/config.py`, then merged with `config.toml` in the active data directory. Secrets are separate. This split matters because normal configuration can be shown, copied, and committed as examples, while API keys should stay masked and local.

The configuration system is intentionally boring: it is a layered set of TOML values and environment variables. That makes it easy to answer "why did this run behave this way?" by checking the active data directory, the config file, and any environment overrides.

## Data directory resolution

Order:

1. `--data-dir PATH`
2. `SRP_DATA_DIR`
3. local `.skill-data` if that directory exists
4. `~/.social-research-probe`

Use `--data-dir` when you want one command to use a specific workspace. Use `SRP_DATA_DIR` when a shell session, CI job, or scripted workflow should consistently use the same directory. Use `.skill-data` when a project should carry its own local state during development. Use the home directory default for personal long-lived settings.

## Main sections

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

Think of gates as switches at different heights. A stage gate disables a whole part of the pipeline. A service gate disables one service inside that part. A technology gate disables one concrete provider or implementation. Prefer the narrowest gate that solves the problem: turn off `technologies.tavily` if only Tavily should be skipped, but turn off a service when the entire category should be skipped.

`srp watch run` requires SQLite persistence. It fails clearly if `database.enabled=false`, `services.persistence.sqlite=false`, `technologies.sqlite_persist=false`, or the platform persist stage is disabled. Watch tests should monkeypatch the research runner and use temporary data directories; they should not make network calls.

`srp watch run --notify` and `srp watch run-due --notify` send notifications only for newly created alert events. `notifications.enabled=false` disables sending globally. Channel-specific `enabled=false` disables that channel even when it is requested explicitly. Notification delivery attempts are recorded locally in SQLite when possible, but delivery failures do not fail the watch run.

`srp schedule cron` and `srp schedule launchd` print local helper configuration only. They include the active `--data-dir` in generated commands and do not install cron entries, load launchd jobs, or start a daemon.

## Secrets

Secrets can come from environment variables such as `SRP_YOUTUBE_API_KEY` or from `secrets.toml`. Environment variables win. The secrets file is written with `0600` permissions.

Use environment variables for CI, temporary shells, and secrets managed by another tool. Use `srp config set-secret` for local development when you want the value stored in the data directory. If a provider is configured but its secret is missing, the provider should be treated as unavailable rather than silently making unauthenticated calls.
