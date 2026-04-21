# Security

[Home](README.md) → Security

---

## Scope

`srp` is a local CLI tool. It runs on the operator's machine, calls third-party APIs over HTTPS, and stores results on the local filesystem. There is no server, no shared database, and no multi-user access control.

For the responsible-disclosure policy see [SECURITY.md](../SECURITY.md).

---

## Assets

| Asset | Sensitivity |
|---|---|
| `YOUTUBE_API_KEY` | High — quota cost if leaked |
| `EXA_API_KEY` | High — billing |
| `BRAVE_API_KEY` | High — billing |
| `TAVILY_API_KEY` | High — billing |
| Claude / Gemini / Codex API keys | High — billing |
| Research packets and transcripts | Low — public YouTube data |
| `config.toml` | Medium — contains corroboration backend choice, LLM runner name |

---

## Trust Boundaries

```
[ User machine ]
      │
      ▼ HTTPS
[ YouTube Data API v3 ]
[ Exa / Brave / Tavily search APIs ]
[ Claude / Gemini / Codex LLM APIs ]
```

`srp` does not accept inbound network connections. All traffic is outbound HTTPS initiated by the operator.

---

## Secret Storage

Secrets are stored by `srp config set-secret <name>`. The command uses a hidden prompt — the value is never echoed to the terminal.

Secrets are written to `~/.social-research-probe/secrets.toml` with permissions `0600`. The write path is [`commands/config.py:_write_secrets_file`](../social_research_probe/commands/config.py), which:

1. Sets `umask 0o077` before creating the file.
2. Explicitly `chmod 0600` after the write.
3. Is atomic relative to concurrent writers — the file is fully rewritten each time a secret is added or unset.

On every read, `_check_perms()` inspects the file's mode bits and prints a stderr warning if the file is group- or world-readable. Tighten with `chmod 0600 ~/.social-research-probe/secrets.toml` when prompted.

**Never commit secrets to version control.** `.env` files are gitignored. `srp setup` and `srp install-skill` **never overwrite** an existing `secrets.toml` — blank prompts are skipped, existing values are preserved.

---

## Secret Retrieval

All secret reads go through [`read_secret()`](../social_research_probe/commands/config.py), which has one well-defined precedence:

1. **`SRP_<NAME_UPCASE>` environment variable** — always wins if set and non-empty.
2. **`secrets.toml` entry** — used when no env variable is set.

This lets CI inject secrets via env without writing a file, and lets operators override a file value for one-off runs without editing the file.

Corroboration and LLM backends never read `os.environ` directly; they go through `read_secret`, so accidental `os.environ` dumps can never expose secrets.

---

## Validating Configuration

```bash
srp config check-secrets --needed-for research --platform youtube
srp config check-secrets --corroboration exa
```

These commands print `missing` and `present` key lists without revealing the values. Run them after configuration changes to confirm readiness.

---

## Network Egress

Domains contacted during a research run:

| Domain | Purpose |
|---|---|
| `www.googleapis.com` | YouTube Data API v3 |
| `api.exa.ai` | Exa corroboration backend |
| `api.search.brave.com` | Brave corroboration backend |
| `api.tavily.com` | Tavily corroboration backend |
| Anthropic / Google / OpenAI endpoints | LLM ensemble (if configured) |

No telemetry is sent. No data is sent to any Anthropic-operated endpoint unless the Claude LLM runner is configured by the operator.

---

## Data Handling

Fetched video metadata, transcripts, and research packets are written to `~/.social-research-probe/`. These files contain public YouTube data and LLM-generated summaries — no PII beyond what appears in public YouTube metadata.

Packets are not transmitted anywhere. HTML reports are self-contained local files.

---

## Supply Chain

- Dependencies are pinned in `requirements.txt` and `requirements-dev.txt`.
- PyPI releases are published via GitHub Actions OIDC trusted-publishing — no `PYPI_API_TOKEN` secret is stored in the repository.
- The release workflow builds from source and publishes checksums (`sha256sum`) alongside the distribution files.

---

## Logging Hygiene

`utils/progress.py::log` writes progress messages to stderr. It never receives secret values. Exception messages that might contain secret content are caught and replaced with `"[redacted]"` before logging.

---

## Hardening Checklist

- [ ] Run `srp config check-secrets` after any credential rotation.
- [ ] Confirm `~/.social-research-probe/secrets.toml` is `0600` (the read path warns you on startup otherwise).
- [ ] Prefer browser-auth runners (Gemini, Claude CLI) over storing API keys on disk where possible.
- [ ] Review `srp show-pending` before `srp apply-pending` — proposals are LLM-generated.
- [ ] Pin `social-research-probe` to a specific version in automated pipelines.
- [ ] Review the GitHub Actions `release.yml` permissions before forking (it uses `contents: write` and `id-token: write`).

---

## See also

- [SECURITY.md](../SECURITY.md) — responsible-disclosure policy
- [Installation](installation.md) — secret configuration walkthrough
- [Commands](commands.md) — `config set-secret` and `config check-secrets` reference
