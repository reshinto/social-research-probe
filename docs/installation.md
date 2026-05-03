[Back to docs index](README.md)

# Installation

This guide walks you through installing `srp`, storing your API keys, choosing an LLM runner, and verifying that everything works before your first research run.

---

## Requirements

- **Python 3.11+**
- **ffmpeg** on `$PATH` — required only for the Whisper transcript fallback. When a video has no captions (roughly 5–10% of the time), [`platforms/youtube/whisper_transcript.py`](../social_research_probe/technologies/transcript_fetch/whisper.py) uses `yt-dlp` to download the audio track and hands it to OpenAI Whisper for on-device transcription. **Whisper decodes audio through `ffmpeg`** — if `ffmpeg` is not installed, Whisper fails and the pipeline falls back to the video description. Install with `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux). No cloud service is contacted for this step; audio and transcript stay on your machine.

---

## Fastest path — the interactive wizard

The quickest way to get set up is to run `srp setup` after installing. It walks you through the default config, picks an LLM runner, and prompts you to paste each API key one by one. Press **Enter** at any prompt to skip that step; you can re-run the wizard or set individual secrets later.

Here is exactly what appears on your terminal from a fresh machine:

```text
uvx --from social-research-probe srp install-skill
Installed 1 executable: srp
srp CLI installed via uv tool

API key setup — press Enter to skip any key:
  Register: https://console.cloud.google.com/apis/library/youtube.googleapis.com
  YouTube Data API v3 key (required for YouTube search):
  >
  Register: https://brave.com/search/api/
  Brave Search API key (corroboration — paid, no free tier):
  >
  Register: https://dashboard.exa.ai/
  Exa search API key (corroboration — free tier available):
  >
  Register: https://app.tavily.com/
  Tavily search API key (corroboration — free tier: 1000 credits/month):
  >

Default LLM runner — choose which AI backend srp should use:
  1. claude    Claude CLI (claude) — requires Anthropic account
           Register: https://claude.ai/download
  2. gemini    Gemini CLI (gemini) — requires Google account
           Register: https://github.com/google-gemini/gemini-cli
  3. codex     Codex CLI (codex) — requires OpenAI account
           Register: https://github.com/openai/codex
  4. local     Local model via SRP_LOCAL_LLM_BIN env var
  5. none      No LLM — skip all AI features
  Enter number (or press Enter to skip):

Setup complete. Try: srp research "AI safety" "latest-news"
```

Key points:

- **LLM runner is a numbered choice.** Type `1`–`5` and press Enter, or press Enter alone to skip.
- **Every secret prompt shows a "Register:" URL** above the input line so you can open the signup page before pasting.
- **Input is visible, not hidden.** The wizard uses plain input so you can see what you paste — useful if your clipboard contains junk. If you prefer hidden input, use `srp config set-secret <NAME>` instead (that uses `getpass`).
- **Blank input = skip.** Press Enter to leave any key unset. You can add missing keys later with `srp config set-secret <NAME>`.
- **Re-running is safe.** `srp setup` never overwrites an existing `config.toml` or an existing secret you leave blank. The current masked value is shown like `[current: AIza…XXXX]` so you know what is already stored.

After the wizard finishes, verify:

```text
$ srp config show
{
  "llm": {
    "runner": "claude",
    "timeout_seconds": 60
  },
  "corroboration": {
    "backend": "auto",
    "max_claims_per_item": 5,
    "max_claims_per_session": 15
  },
  "platforms": {
    "youtube": {
      "recency_days": 90,
      "max_items": 20,
      "enrich_top_n": 5
    }
  }
}

$ srp config check-secrets --needed-for research --platform youtube
{
  "present": ["youtube_api_key", "exa_api_key"],
  "missing": []
}
```

Then run your first research:

```text
$ srp research "AI safety" "latest-news"
[srp] fetching youtube: AI safety / latest-news
[srp] scored 20 items
[srp] enriching top 5 with transcripts…
[srp] transcript: fetching for 'Stuart Russell on AI alignment' …
[srp] summary: transcript-based for 'Stuart Russell on AI alignment'
[srp] corroborating via exa…
[srp] running statistical analysis…
[srp] HTML report: file:///Users/you/.social-research-probe/reports/ai-safety-youtube-20260420-193000.html

## 1. Topic & Purpose
AI safety — latest-news
…(Markdown summary continues)…
```

The sections below drill into each of those commands if you prefer the manual path (one secret / one setting at a time), or need to change something the wizard already set.

---

## Step 1 — Install

Choose the method that suits your workflow:

### pipx

Installs `srp` into its own isolated virtual environment. It will never conflict with your project dependencies and survives Python upgrades.

```bash
# Install pipx first if you don't have it
brew install pipx        # macOS
pip install pipx         # any OS

pipx install social-research-probe
srp install-skill
```

### uvx

Useful for one-off runs without adding `srp` to any environment. The package is downloaded fresh each time, so use `pip` or `pipx` if you run `srp` regularly.

```bash
# Install uv first if you don't have it
brew install uv          # macOS
curl -LsSf https://astral.sh/uv/install.sh | sh   # any OS

uvx --from social-research-probe srp install-skill
```

or

```bash
uv tool install social-research-probe
srp install-skill
```

### From source (development)

```bash
git clone https://github.com/reshinto/social-research-probe
cd social-research-probe
./install.sh
```

`install.sh` also configures the repository's Git hooks directory (`.githooks/`). This enables a **pre-push hook** that runs automatically before every `git push` and blocks the push if:

- `ruff check --fix` or `ruff format` produce any auto-formatting changes (commit the fixes first)
- `ruff check` reports unfixable lint errors
- Any test in `tests/integration`, `tests/unit`, or `tests/contract` fails
- Unit test coverage of `social_research_probe/` is below 100%

If you already cloned the repo before this hook existed, run:

```bash
git config core.hooksPath .githooks
```

or `make setup` to activate it manually.

---

## Step 2 — Set your YouTube API key

A YouTube Data API v3 key is required for all research runs.

Run:

```bash
srp config set-secret YOUTUBE_API_KEY
```

You will see a prompt with hidden input (the key is not echoed to the terminal):

```
youtube_api_key:
```

Type or paste your key and press Enter. The key is stored in `~/.social-research-probe/secrets.toml` with permissions `0600` — readable only by your user account.

To get a YouTube Data API v3 key:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable "YouTube Data API v3"
3. Create credentials → API key

---

## Step 3 — Choose an LLM runner (optional but recommended)

Without an LLM runner, `srp` still scores and ranks videos, fetches transcripts, and falls back to transcript-derived per-item summaries where possible. The runner-only features stay off: Compiled Synthesis, Opportunity Analysis, and Final Summary show placeholders, `llm_search` corroboration is unavailable, and CLI natural-language query mode is disabled.

Results will show this synthesis placeholder:

```
_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_
```

> **`srp` does not bundle any LLM.** Every runner shells out to a separate CLI tool. You must install and authenticate the runner's CLI on your own machine (via npm, brew, curl, a package manager, or an Ollama install for `local`) **before** setting `llm.runner`. If the CLI is missing, `srp` raises a clear health-check error and falls back to other configured runners.

### Recommended: Gemini CLI (free, no API key)

Gemini CLI authenticates through a browser OAuth flow and runs on Google's free tier for typical research workloads. It also powers the free `llm_search` corroboration backend — one install, two benefits.

```bash
# 1. Install the Gemini CLI (npm, homebrew, or manual — see upstream docs)
npm install -g @google/gemini-cli
# 2. Log in through the browser (opens a tab, no key to copy)
gemini auth login
# 3. Point srp at it
srp config set llm.runner gemini
```

Gemini is the recommended default because:

- **No API key stored on disk** — OAuth tokens are managed by the CLI itself.
- **Free tier covers most research loads** — `srp` only calls the LLM for top-N summaries and a synthesis step, so token usage is bounded.
- **One tool, two roles** — the same `gemini` binary is used by the `llm_search` corroboration backend, so you get free web-search corroboration with zero extra setup.

### Other runners

```bash
srp config set llm.runner claude    # Anthropic Claude (requires claude CLI, paid)
srp config set llm.runner codex     # OpenAI Codex (requires codex CLI, paid)
srp config set llm.runner local     # Local model via SRP_LOCAL_LLM_BIN (e.g. ollama)
srp config set llm.runner none      # Disable LLM entirely (default)
```

Each runner calls the respective CLI binary as a subprocess, so the relevant CLI tool must be installed and authenticated separately:

```bash
# Claude example
npm install -g @anthropic-ai/claude-code
claude auth
srp config set llm.runner claude
```

Each runner pins a default model via `extra_flags` (e.g. `--model claude-haiku-4-5` for Claude). Override in `config.toml`:

```toml
[llm.claude]
extra_flags = ["--model", "claude-sonnet-4-6"]
```

See [llm-runners.md](llm-runners.md) for the full comparison, pinned model table, ensemble behaviour, and troubleshooting.

---

## Step 4 — Add corroboration keys (optional)

Corroboration cross-checks each top-N video's claims against independent web sources. Without a search API key, `srp` can still use `llm_search` through your configured LLM runner's native web-search capability; otherwise corroboration is skipped.

```bash
srp config set-secret exa_api_key      # Exa neural search — exa.ai
srp config set-secret brave_api_key    # Brave Search API — api.search.brave.com
srp config set-secret tavily_api_key   # Tavily — tavily.com
```

Each prompts for the value with hidden input, the same as the YouTube key. You only need one; `srp` auto-discovers all available backends when `corroboration.backend = auto` (the default).

---

## Step 5 — Verify setup

```bash
srp config show
```

You will see all current settings printed as a JSON object, for example:

```json
{
  "llm": {
    "runner": "claude",
    "timeout_seconds": 60,
    ...
  },
  "corroboration": {
    "backend": "auto",
    ...
  },
  "platforms": {
    "youtube": {
      "max_items": 20,
      "recency_days": 90,
      ...
    }
  }
}
```

Then check your secrets:

```bash
srp config check-secrets --needed-for research --platform youtube
```

Output shows which keys are present (masked) and which are missing:

```json
{
  "present": ["youtube_api_key"],
  "missing": []
}
```

If `missing` is non-empty, run `srp config set-secret <KEY_NAME>` for each missing key before continuing.

---

## Step 6 — Install the Claude Code skill bundle (optional)

To use `srp` directly from a Claude Code session as `/srp`:

```bash
srp install-skill
```

Output confirms where the files were copied:

```
Skill installed to /Users/<you>/.claude/skills/srp
```

Restart Claude Code, then test:

```
/srp research "AI safety" "latest-news"
```

In skill mode, Claude uses the host model for the language-only steps when `llm.runner = none`. If you explicitly set `llm.runner` to `claude`, `gemini`, `codex`, or `local`, the skill defers to that configured runner instead of duplicating the work in the host model.

---

## Troubleshooting

| Problem                                                                         | Fix                                                           |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `ffmpeg not found`                                                              | `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| `youtube_api_key missing`                                                       | Run `srp config set-secret youtube_api_key`                   |
| Compiled Synthesis / Opportunity Analysis / Final Summary show placeholder text | Set `llm.runner` to a configured provider (Step 3)            |
| Corroboration skipped                                                           | Add at least one corroboration key (Step 4)                   |
| `ModuleNotFoundError: social_research_probe`                                    | Run `pip install -e .` from the repo root                     |

---

## Re-running setup safely

`srp setup` and `srp install-skill` are **idempotent**:

- Existing `config.toml` values are **never overwritten** — the wizard adds missing keys/sections from the bundled template and prints what it added.
- Existing `secrets.toml` is **never overwritten by setup** — the wizard shows a masked preview and prompts; pressing Enter skips the key.
- `secrets.toml` is always written with `0600` permissions; `srp` warns on every read if the file is world- or group-readable.

See [configuration.md](configuration.md#what-happens-when-configtoml-already-exists) for the full lifecycle.

---

## Uninstall

### pipx

```bash
pipx uninstall social-research-probe

rm -rf ~/.social-research-probe        # removes config, secrets, reports, and charts
```

### uvx (uninstall via uv)

```bash
uv tool uninstall social-research-probe

rm -rf ~/.social-research-probe        # removes config, secrets, reports, and charts
```

### From source (development)

```bash
./uninstall.sh

rm -rf ~/.social-research-probe        # removes config, secrets, reports, and charts
```

---

## See also

- [Usage Guide](usage.md) — run your first research and understand the output
- [Configuration](configuration.md) — every config key and its default
- [LLM Runners](llm-runners.md) — runner comparison and why Gemini CLI is the free default
- [Security](security.md) — how secrets are stored and read at runtime
