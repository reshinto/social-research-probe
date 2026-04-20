# Installation

[Home](README.md) → Installation

---

## Requirements

- **Python 3.11+**
- **ffmpeg** on `$PATH` — required only for the Whisper transcript fallback (YouTube captions are tried first; most videos have them)
- No display required — charts render headlessly via matplotlib

---

## Install methods

### pip

Standard install into the current Python environment:

```bash
pip install social-research-probe
```

### pipx (recommended for CLI tools)

Installs `srp` into its own isolated environment so it never conflicts with your project dependencies:

```bash
pipx install social-research-probe
```

[pipx](https://pipx.pypa.io) must be installed first: `brew install pipx` (macOS) or `pip install pipx`.

### uvx (run without installing)

Run a one-off research command without a permanent install:

```bash
uvx social-research-probe research "AI safety" "latest-news"
```

For repeated use, `pip` or `pipx` is faster (no re-download on each run).

[uv](https://docs.astral.sh/uv/) must be installed first: `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`.

### From source (development)

```bash
git clone https://github.com/reshinto/social-research-probe
cd social-research-probe
pip install -e '.[dev]'
```

The `[dev]` extra adds `pytest`, `ruff`, `respx`, `pytest-asyncio`, and other tools needed to run tests.

---

## Verify the install

```bash
srp --version
srp config show
srp config check-secrets --needed-for research --platform youtube
```

If `missing` lists any keys, configure them before running research.

---

## Secret configuration

Secrets are stored on disk with a hidden prompt — never echoed to the terminal or stored in environment variables.

```bash
srp config set-secret YOUTUBE_API_KEY      # required
srp config set-secret EXA_API_KEY          # optional — corroboration
srp config set-secret BRAVE_API_KEY        # optional — corroboration
srp config set-secret TAVILY_API_KEY       # optional — corroboration
```

Copy `.env.example` at the repo root to see every supported key and its purpose. At least one corroboration key is recommended; without one, corroboration runs in `llm_cli` mode (requires `llm.runner` configured) or is skipped entirely.

---

## Install the Claude Code skill bundle

To use `srp` from inside a Claude Code session as `/srp`:

```bash
srp install-skill
```

This copies the skill bundle to `~/.claude/skills/srp/`. Restart Claude Code after running the command, then test with:

```
/srp research "AI safety" "latest-news"
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg not found` | `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) — only needed for Whisper fallback |
| `YOUTUBE_API_KEY missing` | `srp config set-secret YOUTUBE_API_KEY` |
| Blank charts on macOS | Set `MPLBACKEND=Agg` if you see a display error |
| `ModuleNotFoundError: social_research_probe` | `pip install -e .` from the repo root |
| `uvx` re-downloads every run | Use `pip` or `pipx` for repeated use |

---

## Uninstall

```bash
pip uninstall social-research-probe       # or: pipx uninstall social-research-probe
rm -rf ~/.social-research-probe           # removes data directory, config, and reports
```

---

## See also

- [Usage Guide](usage.md) — first research run and all commands
- [Security](security.md) — where secrets are stored and how they are read
