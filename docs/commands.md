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

Apply selected pending purpose IDs:

```bash
srp apply-pending --purposes 1,3
```

Discard selected pending topic IDs:

```bash
srp discard-pending --topics 2,4
```

Expected output for apply/discard:

```json
{
  "ok": true
}
```

## Configuration

Config commands read and write the active data directory.

### Show merged config

```bash
srp config show
```

Expected output shape:

```text
data_dir: /Users/example/.social-research-probe
config_file: /Users/example/.social-research-probe/config.toml
secrets_file: /Users/example/.social-research-probe/secrets.toml

[config]
{
  "llm": {
    "runner": "none",
    "timeout_seconds": 60
  }
}

[secrets]
  youtube_api_key: abcd...wxyz  (from file)
```

### Show paths

```bash
srp config path
```

Expected output shape:

```text
config: /Users/example/.social-research-probe/config.toml
secrets: /Users/example/.social-research-probe/secrets.toml
```

### Set a config value

```bash
srp config set llm.runner gemini
srp config set platforms.youtube.enrich_top_n 3
srp config set technologies.tavily false
```

Expected output:

```text
(no stdout on success)
```

Values are parsed as booleans, integers, floats, or strings. Keys are dotted TOML paths.

### Set or remove a secret

```bash
srp config set-secret youtube_api_key
```

The command prompts for the value unless `--from-stdin` is used:

```bash
printf '%s' "$YOUTUBE_API_KEY" | srp config set-secret youtube_api_key --from-stdin
```

Expected output:

```text
(no stdout on success)
```

Remove a secret:

```bash
srp config unset-secret youtube_api_key
```

Expected output:

```text
(no stdout on success)
```

### Check secrets

```bash
srp config check-secrets --needed-for research --platform youtube --corroboration brave
```

Expected output shape:

```json
{
  "required": ["youtube_api_key", "brave_api_key"],
  "optional": ["exa_api_key", "tavily_api_key"],
  "present": ["youtube_api_key"],
  "missing": ["brave_api_key"]
}
```

## Corroborate claims

Use this when you already have claims in a JSON file and want provider evidence without running a full research pipeline.

Input file:

```json
{
  "claims": [
    {
      "text": "Example claim to check",
      "source_text": "Longer paragraph where the claim appeared"
    }
  ]
}
```

Command:

```bash
srp corroborate-claims --input claims.json --providers brave,exa --output evidence.json
```

Expected output file shape:

```json
{
  "results": [
    {
      "claim_text": "Example claim to check",
      "results": [],
      "aggregate_verdict": "inconclusive",
      "aggregate_confidence": 0.0
    }
  ]
}
```

Exact fields inside each result depend on the provider implementation and available evidence.

## Watch topics and alerts

Use `watch` for local-first monitoring. Watch definitions, watch run history, and alert events are stored in the local SQLite database under the active data directory.

Create a watch:

```bash
srp watch add --topic "AI coding agents" --platform youtube --purpose latest-news
```

List watches:

```bash
srp watch list
srp watch list --output json
```

Run one watch or all enabled watches:

```bash
srp watch run
srp watch run WATCH_ID
srp watch run --notify
srp watch run WATCH_ID --notify --channel file
```

Each watch run executes the normal research pipeline, requires SQLite persistence, compares the new run to the previous matching run when one exists, evaluates deterministic alert rules, and records the result locally. One failed watch does not stop other watches in the same command. Notifications are sent only when `--notify` is passed.

Run watches that are due based on their configured interval:

```bash
srp watch run-due
srp watch run-due --notify
```

Supported intervals are `hourly`, `daily`, and `weekly`. A watch with no interval is manual-only and is skipped by `run-due`. A watch that has never run is due immediately. Unsupported intervals are skipped with a clear message rather than failing the whole command.

List alerts:

```bash
srp watch alerts
srp watch alerts --watch-id WATCH_ID --output markdown
```

Add a custom alert rule:

```bash
srp watch add \
  --topic "AI coding agents" \
  --platform youtube \
  --purpose latest-news \
  --alert-rule '{"metric":"new_claims_count","op":">=","value":5,"severity":"warning"}'
```

Supported rule metrics include `new_narratives_count`, `new_claims_count`, `new_sources_count`, `claims_needing_review`, `rising_risk_score`, `growing_opportunity_score`, `trend_signal_type`, and `narrative_type`.

Test a notification channel:

```bash
srp notify test --channel console
srp notify test --channel file
srp notify test --channel telegram
```

Notifications are local-first. Console and file channels are local. Telegram is optional, disabled by default, and reads token/chat ID from environment variable names configured in `config.toml`; secrets are not stored in SQLite.

Print local scheduling helpers:

```bash
srp schedule cron
srp schedule launchd
srp schedule launchd --output-path ~/Library/LaunchAgents/local.social-research-probe.watch-run-due.plist
```

Schedule helpers print commands that run `srp watch run-due --notify` with the active `--data-dir`. They do not install cron entries, load launchd jobs, start a daemon, or contact a hosted scheduler.

## Render charts and stats from a saved packet

Use `render` when you have a saved report or packet JSON and want chart/stat output for the top-N overall scores.

```bash
srp render --packet packet.json --output-dir ./charts
```

Expected output shape:

```json
{
  "stats": [
    {
      "name": "mean",
      "value": 0.71,
      "caption": "Mean overall_score: 0.71"
    }
  ],
  "chart": {
    "path": "./charts/overall_score_line.png",
    "caption": "Line chart: overall_score over 6 data points"
  }
}
```

## Re-render an HTML report

Use `report` when you have a saved packet/report JSON and want to render HTML again, optionally replacing generated text sections.

```bash
srp report \
  --packet packet.json \
  --compiled-synthesis compiled.md \
  --opportunity-analysis opportunity.md \
  --final-summary summary.md \
  --out report.html
```

Expected stderr when `--out` is used:

```text
[srp] Serve report: srp serve-report --report report.html
```

If `--out` is omitted, the HTML is written to stdout.

## Serve an HTML report

Use `serve-report` to open a local HTTP server for an existing HTML report. This also proxies Voicebox API calls through the same origin.

```bash
srp serve-report --report report.html --host 127.0.0.1 --port 8000
```

Expected output shape:

```text
[srp] Report server: http://127.0.0.1:8000/
```

The command keeps running until interrupted.

## Install skill

Install the Claude Code skill files.

```bash
srp install-skill
srp install-skill --target ~/.claude/skills/srp
```

Expected output shape:

```text
Skill installed to /Users/example/.claude/skills/srp
```

After installation and a Claude Code restart, use the CLI through `/srp`:

```text
/srp research "AI safety" "latest-news"
/srp config show
```

Everything after `/srp` is the same argument list you would pass after `srp` in
a terminal.

Skill behavior:

| Topic | Behavior |
| --- | --- |
| Install location | Default target is `~/.claude/skills/srp`. |
| Discovery | Restart Claude Code after install or refresh. |
| Command mapping | `/srp research ...` maps to `srp research ...`. |
| Secrets | Use `srp config set-secret`; do not paste API keys into chat. |
| Failures | Nonzero exits should show stderr and the exit code. |
| Source of truth | CLI output and files, not generated guesses. |

Troubleshooting:

| Symptom | What to check |
| --- | --- |
| `/srp` is not recognized. | Run `srp install-skill` again and restart Claude Code. |
| `/srp` says `srp` is not found. | Confirm `srp --version` works in the same environment. |
| Summaries or synthesis are missing. | Check `llm.runner`, runner health, and provider configuration. |
| Research cannot start. | Run `srp config check-secrets --needed-for research --platform youtube --output json`. |

## Setup

Run first-time setup or refresh missing config keys.

```bash
srp setup
```

Expected behavior:

- creates the data directory if needed.
- writes missing config defaults without removing existing values.
- prompts for optional runner and secret configuration.

The command is interactive, so exact output depends on the current local state.
