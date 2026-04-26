[Back to docs index](README.md)

# Usage

![CLI command surface](diagrams/command-surface.svg)

Use `srp research` for the main workflow:

```bash
srp research "model collapse" "latest-news"
srp research youtube "AI agents" "latest-news,trends"
srp --data-dir ./.skill-data research "climate tech" "emerging-research"
```

The simple form is `srp research [platform] TOPIC PURPOSES`. `PURPOSES` is comma-separated. If the platform is omitted, YouTube is used.

Think of a research command as three decisions:

| Decision | Example | Meaning |
| --- | --- | --- |
| Platform | `youtube` | Which source adapter should fetch candidate items. |
| Topic | `"AI agents"` | What subject to investigate. |
| Purpose | `"latest-news,trends"` | What research lens should guide ranking and synthesis. |

The current default platform is YouTube because it is the first implemented adapter. The command shape includes a platform position so future adapters can use the same workflow.

Useful flags:

| Flag | Effect |
| --- | --- |
| `--no-shorts` | Exclude YouTube Shorts under 90 seconds. |
| `--no-transcripts` | Skip transcript fetching for speed. |
| `--no-html` | Skip writing the HTML report. |
| `--data-dir PATH` | Use a specific data directory for config, cache, and outputs. |
| `--verbose` | Show more runtime output. |

Topic and purpose state is local JSON:

```bash
srp show-topics
srp update-topics --add "AI safety"
srp show-purposes
srp update-purposes --add 'latest-news=Find recent reporting and claims'
```

The suggestion workflow stages generated ideas before applying them:

```bash
srp suggest-topics --count 5
srp show-pending
srp apply-pending --topics all --purposes all
srp discard-pending --topics all --purposes all
```

Reports can be rebuilt or served:

```bash
srp report --packet packet.json --out report.html
srp serve-report --report ~/.social-research-probe/reports/example.html
```

Use `report` when you already have a saved packet and want to regenerate HTML after changing authoring sections or report formatting. Use `serve-report` when you want to inspect an HTML report in a browser without moving files around.

## Reading a run

After a run, inspect the output in this order:

1. Confirm the report path printed by the command.
2. Open the HTML report for the human-readable view.
3. Check chart PNGs when you need visual evidence.
4. Check the packet or cached stage outputs when a section looks incomplete.
5. Check config and provider health if summaries or corroboration are missing.

Missing generated text does not always mean the run failed. It can mean the selected runner was `none`, a provider was disabled, a secret was missing, or the relevant item did not make the top-N enrichment cutoff.
