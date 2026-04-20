# Command Reference

[Home](README.md) → Commands

---

## Global Options

| Flag | Description |
|---|---|
| `--data-dir PATH` | Override the data directory (default: `~/.social-research-probe`, env: `SRP_DATA_DIR`) |
| `--version` | Print the installed version and exit |
| `--help` | Print help for a command |

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

### `srp update-topics`

```bash
srp update-topics --add "<topic>"
srp update-topics --remove "<topic>"
```

### `srp suggest-topics`

Generate LLM-driven topic suggestions and add them to the pending queue.

---

## Purpose Management

### `srp show-purposes`

Print all registered purposes as JSON.

### `srp update-purposes`

```bash
srp update-purposes --add "<name>"="<description>"
srp update-purposes --remove "<name>"
```

### `srp suggest-purposes`

Generate LLM-driven purpose suggestions and add them to the pending queue.

---

## Pending Proposal Workflow

### `srp show-pending`

Print pending topic and purpose proposals.

### `srp apply-pending`

Accept all pending proposals, merging them into the registered topics and purposes.

### `srp discard-pending`

Reject all pending proposals without applying them.

---

## Configuration

### `srp config show`

Print all current settings.

### `srp config set <key> <value>`

```bash
srp config set llm.runner claude
srp config set corroboration.backend host
```

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
