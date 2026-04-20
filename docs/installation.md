# Installation

[Home](README.md) → Installation

---

## Requirements

- Python 3.11 or later
- `ffmpeg` on `$PATH` — required for the Whisper transcript fallback (YouTube captions are tried first)
- `matplotlib` backend — charts are rendered headlessly; no display required

---

## Install from PyPI

```bash
pip install social-research-probe
srp --version
```

---

## Install from Source

```bash
git clone https://github.com/user/social-research-probe
cd social-research-probe
pip install -e '.[dev]'
srp --version
```

The `[dev]` extra adds `pytest`, `ruff`, `respx`, `pytest-asyncio`, and other dev dependencies.

---

## Verify the Install

```bash
srp --version
srp config show
srp config check-secrets --needed-for research --platform youtube
```

If `missing` lists any keys, configure them before running research (see [Secret Configuration](#secret-configuration) below).

---

## Secret Configuration

Secrets are stored on disk by `srp config set-secret`. The command prompts for the value with a hidden input — never paste API keys into chat or version control.

```bash
srp config set-secret YOUTUBE_API_KEY
srp config set-secret EXA_API_KEY       # optional — corroboration
srp config set-secret BRAVE_API_KEY     # optional — corroboration
srp config set-secret TAVILY_API_KEY    # optional — corroboration
```

Copy `.env.example` at the repo root to see every supported key and its purpose.

---

## Install the Claude Code Skill Bundle

To use `srp` from inside a Claude Code session as `/srp`:

```bash
srp install-skill
```

This copies the skill bundle to `~/.claude/skills/srp/`. Restart Claude Code after running the command.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg not found` | Install ffmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| `YOUTUBE_API_KEY missing` | Run `srp config set-secret YOUTUBE_API_KEY` |
| Blank charts on macOS | Set `MPLBACKEND=Agg` if you see a display error |
| `ModuleNotFoundError: social_research_probe` | Run `pip install -e .` from the repo root |

---

## Uninstall

```bash
pip uninstall social-research-probe
rm -rf ~/.social-research-probe   # removes data directory
```

---

## See also

- [Usage Guide](usage.md) — first research run
- [Security](security.md) — secret storage details
