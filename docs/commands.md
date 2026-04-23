# Command Reference

[Home](README.md) → Commands

---

## Global Options

| Flag | Description |
|---|---|
| `--data-dir PATH` | Override the data directory (default: `~/.social-research-probe`, env: `SRP_DATA_DIR`) |
| `--verbose` | Enable extra progress logging |
| `--version` | Print the installed version and exit |
| `--help` | Print help for a command |

---

## Claude Code Skill

Install the bundled skill once:

```bash
srp install-skill
```

Then run the same commands inside Claude Code by prefixing them with `/srp`:

```text
/srp research "AI safety" "latest-news"
/srp show-topics
/srp update-topics --add '"climate tech"'
/srp show-purposes
/srp update-purposes --add '"emerging-research"="Track peer-reviewed preprints"'
/srp suggest-topics --count 3
/srp show-pending
/srp apply-pending --topics all --purposes all
```

The skill shells out to the CLI for all commands, so flags, quoting, and exit codes are identical. The host LLM remains available for skill-only language work when `llm.runner = none` such as mapping a free-form request to topic + purpose, summarizing the packet inline, and drafting Compiled Synthesis or Opportunity Analysis. If `llm.runner` is set to a concrete provider, prefer the CLI-produced LLM output instead of duplicating it in the host.

---

## `srp research`

Run the five-stage research pipeline for one or more topics.

```bash
srp research <topic> <purpose>
srp research <platform> <topic> <purpose>[,<purpose>…]
srp research [<platform>] "<natural language query>"
```

| Argument | Description |
|---|---|
| `platform` | Platform adapter name (default: `youtube`) |
| `topic` | Registered topic name, or any free-form string |
| `purpose` | Registered purpose name(s), comma-separated |

| Flag | Description |
|---|---|
| `--no-shorts` | Exclude YouTube Shorts (videos under 90 s) |
| `--no-transcripts` | Skip transcript fetching for enriched items |
| `--no-html` | Skip writing the HTML report file |

Outputs a `ResearchPacket` (single topic) or `MultiResearchPacket` (multiple topics) to stdout as JSON, and writes an HTML report to the data directory.

---

## `srp report`

Generate or regenerate an HTML report from an existing packet.

```bash
srp report --packet <path> [--compiled-synthesis <file>] [--opportunity-analysis <file>] [--final-summary <file>] [--out <html-path>]
```

| Flag | Description |
|---|---|
| `--packet PATH` | Path to the JSON packet file (required) |
| `--compiled-synthesis PATH` | File containing Compiled Synthesis |
| `--opportunity-analysis PATH` | File containing Opportunity Analysis |
| `--final-summary PATH` | File containing Final Summary |
| `--out PATH` | Output HTML path (default: auto-generated in data directory) |

---

## Topic Management

### `srp show-topics`

Print all registered topics as JSON.

Flag: `--output text|json|markdown`

### `srp update-topics`

```bash
srp update-topics --add '"ai"|"climate tech"'
srp update-topics --remove '"old topic"'
srp update-topics --rename '"old"->"new"'
```

Flags:
- `--force` overrides duplicate-protection checks
- `--output text|json|markdown`

### `srp suggest-topics`

Generate LLM-driven topic suggestions and add them to the pending queue.

Example: `srp suggest-topics --count 3`

Flags:
- `--count N`
- `--output text|json|markdown`

---

## Purpose Management

### `srp show-purposes`

Print all registered purposes as JSON.

Flag: `--output text|json|markdown`

### `srp update-purposes`

```bash
srp update-purposes --add '"latest-news"="Track new developments and announcements"'
srp update-purposes --remove '"old-purpose"'
srp update-purposes --rename '"old"->"new"'
```

Flags:
- `--force` overrides duplicate-protection checks
- `--output text|json|markdown`

### `srp suggest-purposes`

Generate LLM-driven purpose suggestions and add them to the pending queue.

Example: `srp suggest-purposes --count 3`

Flags:
- `--count N`
- `--output text|json|markdown`

### `srp stage-suggestions`

Accept enhanced suggestions from stdin and add them to the pending queue. Used to round-trip `suggest-topics --output json` output back into pending after enriching it.

```bash
srp suggest-topics --output json \
  | <your-enrichment-step> \
  | srp stage-suggestions --from-stdin
```

---

## Pending Proposal Workflow

### `srp show-pending`

Print pending topic and purpose proposals.

Flag: `--output text|json|markdown`

### `srp apply-pending`

Merge staged proposals into the registered topics and purposes.

```bash
srp apply-pending --topics 1,2 --purposes 4
srp apply-pending --topics all --purposes all
```

Flags:
- `--topics <ids|all>`
- `--purposes <ids|all>`
- `--output text|json|markdown`

### `srp discard-pending`

Remove staged proposals without applying them.

```bash
srp discard-pending --topics 1,2 --purposes 4
srp discard-pending --topics all --purposes all
```

Flags:
- `--topics <ids|all>`
- `--purposes <ids|all>`
- `--output text|json|markdown`

---

## Configuration

### `srp config show`

Print all current settings.

### `srp config set <key> <value>`

```bash
srp config set llm.runner claude
srp config set corroboration.backend auto
srp config set platforms.youtube.max_items 50     # how many videos to fetch (default: 20)
srp config set platforms.youtube.recency_days 30  # how far back to search in days (default: 90)
srp config set platforms.youtube.enrich_top_n 10  # how many top videos get transcripts + summaries (default: 5)
```

All settings and their defaults:

| Key | Default | Description |
|---|---|---|
| `llm.runner` | `none` | LLM provider: `claude`, `gemini`, `codex`, `local`, or `none` |
| `llm.timeout_seconds` | `60` | Seconds before an LLM subprocess call times out |
| `platforms.youtube.max_items` | `20` | Maximum videos fetched per search query |
| `platforms.youtube.recency_days` | `90` | Only return videos published within this many days |
| `platforms.youtube.enrich_top_n` | `5` | How many top-scored videos receive transcript fetch, LLM summary, and corroboration |
| `platforms.youtube.cache_ttl_search_hours` | `6` | How long to cache search results |
| `platforms.youtube.cache_ttl_channel_hours` | `24` | How long to cache channel metadata |
| `corroboration.backend` | `auto` | `auto`, `llm_search`, `exa`, `brave`, `tavily`, or `none` |
| `corroboration.max_claims_per_item` | `5` | Maximum claims checked per enriched item |
| `corroboration.max_claims_per_session` | `15` | Total claim budget per research run |

> **Note on enrichment budget:** The `enrich_top_n` setting controls how many of the top-scored videos receive full enrichment (transcripts, LLM summaries, corroboration). The default is 5 — this balances report quality against transcript-fetch latency and LLM token cost. Increasing `max_items` gives the scoring stage more candidates to rank, and increasing `enrich_top_n` extends the full-enrichment pipeline to more of them. Example:
>
> ```bash
> srp config set platforms.youtube.max_items 100     # rank a larger candidate pool
> srp config set platforms.youtube.enrich_top_n 15   # enrich the top 15 instead of 5
> ```
>
> Keep in mind that transcript fetch + Whisper fallback + LLM summary each add per-item latency, so runs with a large `enrich_top_n` will take proportionally longer.

### `srp config set-secret <name>`

Prompt for a secret value (hidden input) and store it on disk. Never echoes the value.

```bash
srp config set-secret youtube_api_key
srp config set-secret exa_api_key
```

### `srp config check-secrets`

```bash
srp config check-secrets --needed-for research --platform youtube
srp config check-secrets --corroboration exa
```

Prints `missing` and `present` keys. Exit code 0 even if keys are missing (to allow scripting).

### `srp config path`

Prints the resolved path to `config.toml`. Useful in scripts.

### `srp config unset-secret <name>`

Removes one secret from `secrets.toml`. No error if the key is already absent.

---

## Setup & Skill Installation

### `srp setup`

Interactive first-run wizard. Safe to re-run:

- Copies `config.toml.example` → `~/.social-research-probe/config.toml` on first run.
- On re-run, **additively merges** new keys/sections from the bundled template into your existing file. Existing values are never overwritten.
- Prompts for API keys and writes them to `secrets.toml` with mode `0600`. Skips any key you leave blank; never overwrites an existing secret you do not replace.
- Prompts for a default LLM runner and writes it via `config set llm.runner <name>`.

### `srp install-skill`

Copy the Claude Code skill bundle to `~/.claude/skills/srp/` and install the `srp` CLI via `uv tool` or `pipx`:

```bash
srp install-skill
srp install-skill --target ~/.claude/skills/srp
```

Also triggers the same config/secret flow as `setup` — re-running is safe.

---

## Post-hoc Tools

### `srp corroborate-claims`

Run claim corroboration standalone against a JSON file of claims. Useful for reprocessing an existing packet without re-running the fetch/score stages.

```bash
srp corroborate-claims --input claims.json --backends llm_search,tavily --output out.json
```

### `srp render`

Re-render charts and stats for a previously saved packet JSON without re-running the pipeline.

```bash
srp render --packet ~/.social-research-probe/reports/<name>.json --output-dir ./charts
```

### `srp report` (post-hoc synthesis)

See the top of this page for `srp report` fields. The command **bypasses the LLM runner** — the packet stays as-is; only Compiled Synthesis, Opportunity Analysis, and Final Summary are replaced with your files. See [synthesis-authoring.md](synthesis-authoring.md) for the author templates.

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success (may include warnings) |
| `2` | Validation or argument parse error |
| `3` | Duplicate conflict — retry with `--force` |
| `4` | Adapter or subprocess failure |
| `5` | Schema migration failure |

---

## Environment Variables

| Variable | Description |
|---|---|
| `SRP_DATA_DIR` | Override the data directory (default: `~/.social-research-probe`) |
| `SRP_LOGS` | Set to `1` to enable stderr service logs for fetch/enrich/corroborate stages |
| `SRP_DISABLE_CACHE` | Set to `1` to bypass all `utils/pipeline_cache.py` caching |
| `SRP_FAST_MODE` | Set to `1` for clamped top-N + narrower backend set (iteration/debugging) |
| `SRP_LOCAL_LLM_BIN` | Binary path for `llm.runner = "local"` |
| `SRP_TEST_USE_FAKE_YOUTUBE` | Set to `1` to activate the fake YouTube adapter (tests only) |
| `SRP_TEST_USE_FAKE_CORROBORATION` | Set to `1` to activate fake corroboration backends (tests only) |
| `SRP_YOUTUBE_API_KEY` | Overrides `secrets.toml` value for `youtube_api_key` |
| `SRP_EXA_API_KEY` / `SRP_BRAVE_API_KEY` / `SRP_TAVILY_API_KEY` | Same env-override pattern for corroboration keys |

The env-override pattern is uniform: `SRP_<NAME_UPCASE>` takes precedence over any matching value in `secrets.toml`.

---

## See also

- [Usage Guide](usage.md) — worked examples
- [Security](security.md) — secret storage details
