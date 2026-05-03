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

## Technology Gates

Technology gates are flat names under `[technologies]`, for example `youtube_search`, `llm_ensemble`, `corroboration_host`, `export_package`, and `sqlite_persist`. Unknown technology names are disabled.

## Secrets

`commands/config.py` maps logical secret names to environment variables by uppercasing and prefixing `SRP_`.

| Logical name | Environment variable |
| --- | --- |
| `youtube_api_key` | `SRP_YOUTUBE_API_KEY` |
| `exa_api_key` | `SRP_EXA_API_KEY` |
| `brave_api_key` | `SRP_BRAVE_API_KEY` |
| `tavily_api_key` | `SRP_TAVILY_API_KEY` |

Secret file values live in `[secrets]` in `secrets.toml`. Environment variables win over file values.
