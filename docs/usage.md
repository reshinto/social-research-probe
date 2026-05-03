[Back to docs index](README.md)

# Usage

![CLI command surface](diagrams/command-surface.svg)

Use `srp research` for the main workflow:

```bash
srp research youtube "model collapse" "latest-news"
srp research youtube "AI agents" "latest-news,trends" --no-shorts
srp --data-dir ./.skill-data research youtube "climate tech" "emerging-research"
```

The command shape is:

```bash
srp research [platform] TOPIC PURPOSES
```

`PURPOSES` is comma-separated. If `platform` is omitted, the parser targets `all`, which runs every registered concrete platform. In the current repository, YouTube is the only concrete platform.

You can also pass one natural-language query instead of explicit topic and purposes:

```bash
srp research youtube "Find recent credible evidence about model collapse"
```

That path asks the configured structured LLM runner to classify the query into a topic and purpose. If no runner is configured, prefer the explicit `TOPIC PURPOSES` form.

## Decisions In One Command

| Decision | Example | Meaning |
| --- | --- | --- |
| Platform | `youtube` | Which source adapter fetches evidence. |
| Topic | `"AI agents"` | The subject to investigate. |
| Purpose | `"latest-news,trends"` | The research lens that affects purpose merge, ranking weights, and synthesis. |
| Data dir | `--data-dir ./.skill-data` | Where config, secrets, cache, reports, exports, and DB are read/written. |

## Useful Flags

| Flag | Effect |
| --- | --- |
| `--no-shorts` | Exclude YouTube Shorts under 90 seconds. |
| `--no-transcripts` | Skip transcript fetching for top-N items. |
| `--no-html` | Skip HTML output and use Markdown fallback behavior. |
| `--data-dir PATH` | Use a specific data directory. This is a global flag before the command. |
| `--verbose` | Show more runtime output. |
| `--version` | Print installed version and package path. |

## Everyday Workflow

1. Run `srp setup` or configure manually.
2. Confirm paths with `srp config path`.
3. Add a YouTube key with `srp config set-secret youtube_api_key`.
4. Optionally choose a runner with `srp config set llm.runner gemini` and `srp config set technologies.gemini true`.
5. Add or inspect purposes with `srp show-purposes`.
6. Run research.
7. Open the printed report path or serve command.
8. Inspect exports, charts, and database rows if you need machine-readable follow-up.

## Reading A Run

After a run, inspect output in this order:

1. **Command stdout**: usually a `srp serve-report --report ...` command, or a Markdown path if HTML was skipped or failed.
2. **HTML report**: the human-readable view under `reports/`.
3. **Export package**: CSV/Markdown/JSON files next to the HTML report.
4. **Charts**: PNG files under `charts/`.
5. **SQLite**: `srp db stats`, `srp claims list`, or direct inspection of `srp.db`.
6. **Config and secrets**: if generated sections, comments, transcripts, or corroboration are missing.

Missing generated text does not always mean a failed run. It can mean `llm.runner = "none"`, a runner binary was unavailable, the stage was disabled, a secret was missing, or the relevant item did not make the top-N enrichment cutoff.

## Skill Usage

The bundled skill is a thin operator guide for the same CLI:

```text
/srp research youtube "AI agents" "latest-news"
/srp config show
/srp claims list --needs-review
```

The skill does not define a separate command language. The local `srp` CLI remains the source of truth.
