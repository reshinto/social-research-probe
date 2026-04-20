# Installation

[Home](README.md) → Installation

This guide walks you through installing `srp`, storing your API keys, choosing an LLM runner, and verifying that everything works before your first research run.

---

## Requirements

- **Python 3.11+**
- **ffmpeg** on `$PATH` — only needed for the Whisper transcript fallback when a video has no captions (most do)

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
