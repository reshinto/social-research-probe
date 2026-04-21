# Configuration

[Home](README.md) → Configuration

Everything `srp` reads at runtime lives in two files under the data directory (default: `~/.social-research-probe/`):

| File | Contents | Permissions |
|---|---|---|
| `config.toml` | Non-secret settings: which runner to use, how many items to fetch, which backends are allowed, feature toggles | user-readable |
| `secrets.toml` | API keys and anything sensitive | `0600` (user-only) |

Override the data directory with `--data-dir <path>` or the `SRP_DATA_DIR` environment variable.

---

## config.toml — every key

This is an annotated view of [`config.toml.example`](../social_research_probe/config.toml.example). Every key is optional; missing keys fall back to the defaults shown.

### `[llm]` — LLM runner defaults

```toml
[llm]
runner = "none"          # claude | gemini | codex | local | none
timeout_seconds = 60
```

| Key | Default | What it controls |
|---|---|---|
| `runner` | `none` | The primary LLM runner for CLI summaries, `llm_search` corroboration, and sections 10–11 synthesis. `none` disables runner subprocesses; CLI sections 10–11 stay placeholders, while the Claude Code skill may still use the host model for skill-only language work. |
| `timeout_seconds` | `60` | Per-call wall-clock timeout for the runner subprocess. |

Per-runner subsections (`[llm.claude]`, `[llm.gemini]`, `[llm.codex]`, `[llm.local]`) accept `model`, `binary`, and `extra_flags` — see [LLM Runners](llm-runners.md).

### `[scoring.weights]` — trust/trend/opportunity weights

Defaults: `trust = 0.45`, `trend = 0.30`, `opportunity = 0.25`. Uncomment any subset in `config.toml` to override. Per-purpose overrides (in `purposes/*.json`) take precedence.

### `[corroboration]` — claim corroboration

```toml
[corroboration]
backend = "host"         # host | llm_search | exa | brave | tavily | none
max_claims_per_item = 5
max_claims_per_session = 15
```

| Key | Default | What it controls |
|---|---|---|
| `backend` | `host` | `host` tries every healthy backend; `none` disables corroboration. |
| `max_claims_per_item` | `5` | Upper bound on claims extracted per top-N item. |
| `max_claims_per_session` | `15` | Upper bound across the whole run. |

### `[platforms.youtube]` — YouTube adapter

```toml
[platforms.youtube]
recency_days = 90
max_items = 20
enrich_top_n = 5
cache_ttl_search_hours = 6
cache_ttl_channel_hours = 24
```

| Key | Default | What it controls |
|---|---|---|
| `recency_days` | `90` | Search window upper bound. |
| `max_items` | `20` | How many videos the search fetches. |
| `enrich_top_n` | `5` | How many top-scored items get transcripts + LLM summaries (biggest cost lever). |
| `cache_ttl_search_hours` | `6` | Freshness window for cached search results. |
| `cache_ttl_channel_hours` | `24` | Freshness window for cached channel metadata. |

### `[features]` — toggles for optional stages

Every toggle is **independent**; disabling one never breaks another. Highlights:

| Key | Default | Effect when `false` |
|---|---|---|
| `enrichment_enabled` | `true` | Skip transcripts + summaries entirely. |
| `transcript_fetch_enabled` | `true` | Skip transcripts but still summarise (from title/description). |
| `media_url_summary_enabled` | `true` | Do not send media URLs to Gemini for direct ingestion. |
| `merged_summary_enabled` | `true` | Skip reconciliation of transcript vs URL summaries. |
| `charts_enabled` | `true` | Skip chart generation. |
| `synthesis_enabled` | `true` | Leave sections 10–11 as placeholders even if a runner is configured. |
| `html_report_enabled` | `true` | Skip the HTML report (Markdown is always written as the fallback). |
| `corroboration_enabled` | `true` | Skip corroboration entirely (overrides `backend`). |
| `<backend>_enabled` | `true` | Per-backend gate. `llm_search_enabled` is the runner-agnostic agentic-search backend and is independent of the per-runner `<runner>_service_enabled` gates. |
| `<runner>_service_enabled` | `false` | Whether the runner is eligible for the ensemble fan-out (the primary `llm.runner` is always allowed). `srp install-skill` auto-enables the gate for the runner you select. |

### `[tunables]` — thresholds you rarely need to touch

```toml
[tunables]
summary_divergence_threshold = 0.4
per_item_summary_words = 100
```

### `[logging]`

```toml
[logging]
service_logs_enabled = false   # overridden at runtime by SRP_LOGS=1
```

### Full key list

Run `srp config show --output json` to dump the resolved config. `srp config path` prints the file location.

---

## Changing config

```bash
srp config set llm.runner gemini
srp config set platforms.youtube.max_items 50
srp config set corroboration.backend none
```

Dotted keys traverse TOML tables. The value type is inferred: `50` becomes an integer, `gemini` a string, `true` a boolean. The write preserves other keys and sections.

---

## secrets.toml — API keys

Managed via `srp config set-secret / unset-secret / check-secrets`:

```bash
srp config set-secret youtube_api_key         # hidden prompt
srp config check-secrets --needed-for research --platform youtube --output json
# → {"present": ["youtube_api_key"], "missing": []}
```

Secrets currently recognised:

| Name | Purpose |
|---|---|
| `youtube_api_key` | YouTube Data API v3 (required to run research) |
| `brave_api_key` | Brave Search corroboration backend |
| `exa_api_key` | Exa corroboration backend |
| `tavily_api_key` | Tavily corroboration backend |

Gemini CLI and Claude CLI runners do **not** need API keys — they authenticate through the CLI tool directly (usually a browser login).

### Environment overrides

Any secret can be overridden at runtime:

```bash
SRP_YOUTUBE_API_KEY=... srp research "AI" "latest-news"
```

The env var wins over the file. `read_secret()` in [`commands/config.py`](../social_research_probe/commands/config.py) checks `SRP_<NAME_UPCASE>` first and only falls back to `secrets.toml` if unset.

---

## What happens when config.toml already exists

![Config & secrets lifecycle on setup / install-skill](diagrams/config_lifecycle.svg)


`srp setup` (the interactive wizard) and `srp install-skill` both call `_copy_config_example()` in [`commands/install_skill.py`](../social_research_probe/commands/install_skill.py):

- **Fresh install** — the bundled template is copied verbatim to `~/.social-research-probe/config.toml`.
- **Reinstall** — the existing file is parsed; any keys or sections that exist in the bundled template but not in your file are **additively merged**. Your existing values are **never overwritten**. The wizard prints the dotted key paths it added, so the diff is visible.

This means you can safely re-run `srp setup` after upgrading `srp` — new config keys light up, your customisations stay.

## What happens when secrets.toml already exists

- The file is **never overwritten by setup**. The wizard reads existing values, shows a masked preview (`abc…xyz`), and prompts; an empty response skips the key.
- Writes go through `_write_secrets_file()` which:
  1. Sets `umask 0o077` for the file creation.
  2. Explicitly `chmod 0600` after the write.
- On every read, if the file's permissions are wider than `0600`, `srp` prints a stderr warning ("should be 0600"). Tighten them with `chmod 0600 ~/.social-research-probe/secrets.toml`.
- `SRP_<NAME_UPCASE>` environment variables always win over the file, so secrets.toml can be absent in CI where keys are injected via env.

---

## Config recipes for common objectives

| Objective | Key settings |
|---|---|
| **Cheapest** — free LLM + free corroboration | `llm.runner = "gemini"`, `corroboration.backend = "llm_search"`, `platforms.youtube.enrich_top_n = 3` |
| **Deepest** — everything on | `llm.runner = "claude"`, `corroboration.backend = "host"`, `max_items = 100`, `enrich_top_n = 10` |
| **Fastest** — iterate quickly | `SRP_FAST_MODE=1`, `max_items = 10`, `enrich_top_n = 3` |
| **Offline** — no cloud calls | `llm.runner = "local"`, `corroboration.backend = "none"`, Whisper handles transcripts |

See [Cost Optimization](cost-optimization.md) for the reasoning behind each lever.

---

## See also

- [Installation](installation.md) — step-by-step first-time setup
- [LLM Runners](llm-runners.md) — runner comparison and why Gemini CLI is the free default
- [Corroboration](corroboration.md) — picking backends and their free tiers
- [Security](security.md) — trust boundaries and secret handling
- [Cost Optimization](cost-optimization.md) — how each setting affects what you pay
