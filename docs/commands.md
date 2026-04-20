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

The skill shells out to the CLI, so flags, quoting, and exit codes are identical.

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
srp report --packet <path> [--synthesis-10 <file>] [--synthesis-11 <file>] [--out <html-path>]
```

| Flag | Description |
|---|---|
| `--packet PATH` | Path to the JSON packet file (required) |
| `--synthesis-10 PATH` | File containing section 10 (Compiled Synthesis) |
| `--synthesis-11 PATH` | File containing section 11 (Opportunity Analysis) |
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
srp config set corroboration.backend host
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
| `corroboration.backend` | `host` | `host`, `exa`, `brave`, `tavily`, `llm_cli`, or `none` |
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
srp config set-secret YOUTUBE_API_KEY
srp config set-secret EXA_API_KEY
```

### `srp config check-secrets`

```bash
srp config check-secrets --needed-for research --platform youtube
srp config check-secrets --corroboration exa
```

Prints `missing` and `present` keys. Exit code 0 even if keys are missing (to allow scripting).

---

## Skill Installation

### `srp install-skill`

Copy the Claude Code skill bundle to `~/.claude/skills/srp/`.

```bash
srp install-skill
srp install-skill --target ~/.claude/skills/srp
```

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
| `SRP_DATA_DIR` | Override the data directory |
| `SRP_TEST_USE_FAKE_YOUTUBE` | Set to `1` to activate the fake YouTube adapter (tests only) |
| `SRP_TEST_USE_FAKE_CORROBORATION` | Set to `1` to activate fake corroboration backends (tests only) |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `EXA_API_KEY` | Exa search API key |
| `BRAVE_API_KEY` | Brave Search API key |
| `TAVILY_API_KEY` | Tavily Search API key |

---

## See also

- [Usage Guide](usage.md) — worked examples
- [Security](security.md) — secret storage details
