Before YouTube runs: `srp config check-secrets --needed-for research --platform youtube --output json`; if `missing`, tell user to run `srp config set-secret NAME`.

Forms:
- Explicit: `srp research [PLATFORM] TOPIC PURPOSES`
- Natural language: `srp research [PLATFORM] "QUERY"`

Current platform parse:
- First arg matching registered pipeline is platform (`youtube`, `all`).
- No platform => `all`.
- `PURPOSES` is comma-separated.

Flags:
- `--no-shorts`
- `--no-transcripts`
- `--no-html`

Output: stdout is report access path or `srp serve-report --report ...` command. Surface it. Do not invent missing synthesis unless user explicitly asks for authoring help; CLI/report files are source.
