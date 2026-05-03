# Installation

[Back to docs index](README.md)

This guide gets `srp` from zero to a working local setup. The minimum useful setup is Python, the package, and a YouTube API key. LLM runners, corroboration providers, Whisper fallback, Voicebox narration, exports, and SQLite persistence are optional.

## Requirements

| Requirement | Why |
| --- | --- |
| Python 3.11 or newer | Required by `pyproject.toml`. |
| Shell access | `srp` is a CLI. |
| YouTube API key | Required for live YouTube search, metadata, and comments. |
| Optional runner CLI | Needed only for LLM summaries, synthesis, query classification, or `llm_search`. |
| Optional provider keys | Needed only for Brave, Exa, or Tavily corroboration. |

## Install From PyPI

With `pipx`:

```bash
pipx install social-research-probe
srp --version
```

With `uvx` for one-off execution:

```bash
uvx social-research-probe --version
```

## Install From Source

```bash
git clone https://github.com/reshinto/social-research-probe.git
cd social-research-probe
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
srp --version
```

The repo also includes `install.sh`, but the commands above show the underlying steps.

## Choose A Data Directory

The default is `~/.social-research-probe` unless a local `.skill-data` directory exists. For a project-local setup:

```bash
mkdir -p .skill-data
srp --data-dir ./.skill-data config path
```

For a one-command override:

```bash
srp --data-dir ./research-data config path
```

For a shell-session override:

```bash
export SRP_DATA_DIR="$PWD/research-data"
srp config path
```

## Run Setup

The interactive setup command creates default config when missing and prompts for common secrets:

```bash
srp setup
```

You can also configure manually.

## Add The YouTube Key

```bash
srp config set-secret youtube_api_key
srp config check-secrets --needed-for research --platform youtube --output json
```

Environment variable equivalent:

```bash
export SRP_YOUTUBE_API_KEY="..."
```

Environment variables win over `secrets.toml`.

## Optional LLM Runner

Keep the default `llm.runner = "none"` if you want no hosted model calls. To use a runner, first install and authenticate the runner CLI outside `srp`, then enable it in config.

Example for Gemini:

```bash
srp config set llm.runner gemini
srp config set technologies.gemini true
```

Example for Codex:

```bash
srp config set llm.runner codex
srp config set technologies.codex true
```

Example for Claude:

```bash
srp config set llm.runner claude
srp config set technologies.claude true
```

Runner-specific flags live under `[llm.<runner>]` in `config.toml`. Check [LLM runners](llm-runners.md) and [API costs and keys](api-costs-and-keys.md) before enabling high-volume generated-text work.

## Optional Corroboration Providers

Corroboration checks extracted claims with search providers. Add only the providers you want to use:

```bash
srp config set-secret brave_api_key
srp config set-secret exa_api_key
srp config set-secret tavily_api_key
```

Choose provider mode:

```bash
srp config set corroboration.provider auto
srp config set corroboration.max_claims_per_item 5
srp config set corroboration.max_claims_per_session 15
```

Use `corroboration.provider none` for no corroboration calls.

## Verify The Install

Run an offline synthetic report first:

```bash
srp demo-report
```

Then run a small live research command:

```bash
srp research youtube "AI agents" "latest-news" --no-shorts
```

If HTML succeeds, stdout is usually a serve command:

```text
srp serve-report --report /path/to/reports/<run-id>.html
```

If HTML is disabled or fails, stdout is a Markdown report path.

## Optional Skill Bundle

Install the bundled `/srp` operator skill:

```bash
srp install-skill
```

Default target:

```text
~/.claude/skills/srp
```

You can override the target:

```bash
srp install-skill --target /path/to/skills/srp
```

The skill is manual-only. It tells the host to run the local `srp` CLI and not invent flags or hidden workflows.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `srp` command not found | Confirm your environment has the package script on `PATH`; for source installs activate `.venv`. |
| Config changes ignored | Run `srp config path`; you may be editing another data directory. |
| YouTube fetch fails | Check `youtube_api_key`, quota, and `technologies.youtube_api`. |
| Summaries missing | Check `llm.runner`, runner binary availability, runner technology gate, and timeout. |
| Corroboration skipped | Check provider mode, provider secret, provider technology gate, and claim caps. |
| Charts missing | Check `matplotlib`, `stages.youtube.charts`, `services.youtube.analyzing.charts`, and `technologies.charts_suite`. |
| SQLite missing | Check `[database].enabled`, `stages.youtube.persist`, `services.persistence.sqlite`, and `technologies.sqlite_persist`. |

## Uninstall

For `pipx`:

```bash
pipx uninstall social-research-probe
```

For a source checkout:

```bash
python -m pip uninstall social-research-probe
```

Remove local data only when you intentionally want to delete config, secrets, cache, reports, exports, and database history:

```bash
rm -rf ~/.social-research-probe
```
