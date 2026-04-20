# Installation

[Home](README.md) → Installation

This guide walks you through installing `srp`, storing your API keys, choosing an LLM runner, and verifying that everything works before your first research run.

---

## Requirements

- **Python 3.11+**
- **ffmpeg** on `$PATH` — only needed for the Whisper transcript fallback when a video has no captions (most do)

---

## Fastest path — the interactive wizard

The quickest way to get set up is to run `srp setup` after installing. It walks you through the default config, picks an LLM runner, and prompts you to paste each API key one by one. Press **Enter** at any prompt to skip that step; you can re-run the wizard or set individual secrets later.

Here is exactly what appears on your terminal from a fresh machine:

```text
$ pipx install social-research-probe
  installed package social-research-probe 0.2.0
  These apps are now globally available
    - srp
done! ✨

$ srp setup
Welcome to social-research-probe setup.
This wizard writes a default config and prompts for each API key in turn.
Press Enter at any prompt to skip that step — you can re-run `srp setup`
or `srp config set-secret <name>` later.

Default config written to /Users/you/.social-research-probe/config.toml

Default LLM runner — choose which AI backend srp should use:
  1. claude    Claude CLI (claude) — requires Anthropic account
           Register: https://claude.ai/download
  2. gemini    Gemini CLI (gemini) — requires Google account
           Register: https://github.com/google-gemini/gemini-cli
  3. codex     Codex CLI (codex) — requires OpenAI account
           Register: https://github.com/openai/codex
  4. local     Local model via SRP_LOCAL_LLM_BIN env var
  5. none      No LLM — skip all AI features
  Enter number (or press Enter to skip): 1         ← you type 1 and press Enter
  runner set to 'claude'.

API key setup — press Enter to skip any key:
  Register: https://console.cloud.google.com/apis/library/youtube.googleapis.com
  YouTube Data API v3 key (required for YouTube search):
  > AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXX   ← paste your key, press Enter
    saved.
  Register: https://brave.com/search/api/
  Brave Search API key (corroboration — paid, no free tier):
  >                                           ← just press Enter to skip
  Register: https://dashboard.exa.ai/
  Exa search API key (corroboration — free tier available):
  > abcd1234-ef56-7890-abcd-ef1234567890  ← paste Exa key
    saved.
  Register: https://app.tavily.com/
  Tavily search API key (corroboration — free tier: 1000 credits/month):
  >                                           ← skip Tavily
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
    "backend": "host",
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

### pip

```bash
pip install social-research-probe
```

### pipx (recommended for CLI tools)

Installs `srp` into its own isolated virtual environment. It will never conflict with your project dependencies and survives Python upgrades.

```bash
# Install pipx first if you don't have it
brew install pipx        # macOS
pip install pipx         # any OS

pipx install social-research-probe
```

### uvx (run without a permanent install)

Useful for one-off runs without adding `srp` to any environment. The package is downloaded fresh each time, so use `pip` or `pipx` if you run `srp` regularly.

```bash
# Install uv first if you don't have it
brew install uv          # macOS
curl -LsSf https://astral.sh/uv/install.sh | sh   # any OS

uvx social-research-probe research "AI safety" "latest-news"
```

### From source (development)

```bash
git clone https://github.com/reshinto/social-research-probe
cd social-research-probe
pip install -e '.[dev]'
```

---

## Step 2 — Set your YouTube API key

A YouTube Data API v3 key is required for all research runs.

Run:

```bash
srp config set-secret YOUTUBE_API_KEY
```

You will see a prompt with hidden input (the key is not echoed to the terminal):

```
YOUTUBE_API_KEY:
```

Type or paste your key and press Enter. The key is stored in `~/.social-research-probe/secrets.toml` with permissions `0600` — readable only by your user account.

To get a YouTube Data API v3 key:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable "YouTube Data API v3"
3. Create credentials → API key

---

## Step 3 — Choose an LLM runner (optional but recommended)

Without an LLM runner, `srp` still scores and ranks videos but skips transcript summarisation and report sections 10–11 (Compiled Synthesis and Opportunity Analysis). Results will show a placeholder:

```
_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_
```

To enable LLM features, set `llm.runner` to a provider you have access to:

```bash
srp config set llm.runner claude    # Anthropic Claude (requires claude CLI)
srp config set llm.runner gemini    # Google Gemini (requires gemini CLI)
srp config set llm.runner codex     # OpenAI Codex (requires codex CLI)
srp config set llm.runner local     # Local model via Ollama
srp config set llm.runner none      # Disable LLM entirely (default)
```

Each runner calls the respective CLI binary as a subprocess, so the relevant CLI tool must be installed and authenticated separately. For example, for Claude:

```bash
# Install and authenticate the Anthropic Claude CLI first
npm install -g @anthropic-ai/claude-code
claude auth

# Then tell srp to use it
srp config set llm.runner claude
```

---

## Step 4 — Add corroboration keys (optional)

Corroboration cross-checks each top-5 video's claims against independent web sources. Without a key, `srp` uses `llm_cli` mode (requires `llm.runner` configured) or skips corroboration entirely.

```bash
srp config set-secret EXA_API_KEY      # Exa neural search — exa.ai
srp config set-secret BRAVE_API_KEY    # Brave Search API — api.search.brave.com
srp config set-secret TAVILY_API_KEY   # Tavily — tavily.com
```

Each prompts for the value with hidden input, the same as the YouTube key. You only need one; `srp` auto-discovers all available backends when `corroboration.backend = host` (the default).

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
    "backend": "host",
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
[srp] skill installed → ~/.claude/skills/srp/
```

Restart Claude Code, then test:

```
/srp research "AI safety" "latest-news"
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg not found` | `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| `YOUTUBE_API_KEY missing` | Run `srp config set-secret YOUTUBE_API_KEY` |
| Sections 10–11 show placeholder text | Set `llm.runner` to a configured provider (Step 3) |
| Corroboration skipped | Add at least one corroboration key (Step 4) |
| `ModuleNotFoundError: social_research_probe` | Run `pip install -e .` from the repo root |

---

## Uninstall

```bash
pip uninstall social-research-probe    # or: pipx uninstall social-research-probe
rm -rf ~/.social-research-probe        # removes config, secrets, reports, and charts
```

---

## See also

- [Usage Guide](usage.md) — run your first research and understand the output
- [Security](security.md) — how secrets are stored and read at runtime
