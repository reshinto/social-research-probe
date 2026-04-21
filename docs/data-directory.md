# `~/.social-research-probe/` — Data & Storage Reference

[← Documentation hub](README.md)

This is the canonical reference for every artefact `srp` writes to your
home directory. When you want to know _what_ a file is, _when_ it's written,
_where_ it's read, _who_ writes it, and _why_ it exists — this page is the
single source of truth.

The directory is overridable via the `SRP_DATA_DIR` environment variable,
which every pipeline stage honours (useful in tests, CI, sandboxed runs).
Cache lookups can be bypassed with `SRP_DISABLE_CACHE=1`.

## Layout at a glance

```
~/.social-research-probe/
├── config.toml                 # merged runtime configuration
├── secrets.toml                # API keys (never share)
├── topics.json                 # saved research topics
├── purposes.json               # reusable research profiles
├── pending_suggestions.json    # queued follow-up items
├── cache/                      # per-query cache shards (hashed)
│   ├── fetch/
│   ├── transcript/
│   ├── summary/
│   └── corroboration/
├── charts/                     # generated PNGs per research run
└── reports/                    # generated HTML reports per run
```

## Per-artefact reference

### `config.toml`
| Aspect | Value |
| --- | --- |
| **What** | The resolved, merged active configuration (defaults + user overrides). |
| **When written** | First `srp` run, or any time you execute `srp config set …`. |
| **Where read** | Every pipeline stage via `load_active_config()`. |
| **Who writes** | The CLI / setup command. |
| **Why** | Single source of truth for runtime settings so no module has to redo TOML parsing. |
| **Format** | TOML. Commented; regenerates on upgrade but never overwrites user keys. |
| **Footprint** | ~2–10 KB. |
| **Retention** | Persistent; never rotated. |
| **Safe to delete** | Yes — regenerated on next run from embedded defaults. You lose customizations. |

### `secrets.toml`
| Aspect | Value |
| --- | --- |
| **What** | API keys for providers: YouTube Data API, Brave, Exa, Tavily, Claude, Gemini, Codex, TTS. |
| **When written** | User edits directly, or via `srp config set-secret <name>`. |
| **Where read** | Backend `health_check()` and client init, via `read_runtime_secret(name)`. |
| **Who writes** | User or `srp config set-secret`. |
| **Why** | Separates secrets from `config.toml` so configuration is safely shareable. |
| **Format** | TOML, `0600` permissions recommended. |
| **Footprint** | < 1 KB. |
| **Retention** | Persistent. |
| **Safe to delete** | Yes — you lose access to paid backends until re-populated. |

### `topics.json`
| Aspect | Value |
| --- | --- |
| **What** | User-saved research topics (list of `{name, topic, purpose_set, …}`). |
| **When written** | `srp topic add` / `srp topic remove`. |
| **Where read** | The `srp research` topic picker. |
| **Who writes** | The user, via CLI. |
| **Why** | Persists named queries across sessions. |
| **Format** | JSON array. |
| **Footprint** | KBs. |
| **Safe to delete** | Yes — only loses saved topic names, not research artefacts. |

### `purposes.json`
| Aspect | Value |
| --- | --- |
| **What** | Reusable research profiles: scoring weights, cutoffs, selected backends. |
| **When written** | Setup wizard or manual edit. |
| **Where read** | `srp research --purpose <name>`. |
| **Who writes** | User / setup. |
| **Why** | Lets one user run different research modes without flag gymnastics. |
| **Format** | JSON. |
| **Safe to delete** | Yes — falls back to embedded defaults. |

### `pending_suggestions.json`
| Aspect | Value |
| --- | --- |
| **What** | Queued suggestion items awaiting user review after a run. |
| **When written** | Orchestrator at end of each research run. |
| **Where read** | `srp suggestions review`. |
| **Who writes** | The pipeline. |
| **Why** | A backlog between sessions so actionable items aren't lost. |
| **Format** | JSON array. |
| **Safe to delete** | Yes — you forfeit the backlog, not core research data. |

### `cache/`
| Aspect | Value |
| --- | --- |
| **What** | Per-query cached payloads from fetch, hydrate, transcript, summary, and corroboration stages. |
| **When written** | On first computation of each cache key within TTL. |
| **Where read** | Every stage re-runs: skips the external call on a cache hit. |
| **Who writes** | Pipeline stages via `pipeline_cache.get_json` / `set_json`. |
| **Why** | Massive cost + latency win for re-runs. |
| **Format** | JSON shards keyed by `hash_key(topic, inputs)`. |
| **Footprint** | Can grow to GBs on heavy use. |
| **Retention** | TTL-bounded per sub-cache (see `utils/pipeline_cache.py`). |
| **Safe to delete** | Yes — next run re-fetches, you pay the external API bill again. |
| **Env overrides** | `SRP_DISABLE_CACHE=1` bypasses read + write entirely; useful in tests. |

### `charts/`
| Aspect | Value |
| --- | --- |
| **What** | PNG artefacts produced by every viz renderer during a run (bar, line, scatter, histogram, regression, residuals, heatmap). |
| **When written** | Viz step of the pipeline (`pipeline/charts.py`). |
| **Where read** | Embedded in the HTML report; also openable directly. |
| **Who writes** | The viz renderers. |
| **Why** | Deliverable artefacts + source for HTML report `<img>` tags. |
| **Format** | PNG. |
| **Footprint** | ~10–30 KB each; ~10 files per run. |
| **Safe to delete** | Yes — rendered again on the next run. |

### `reports/`
| Aspect | Value |
| --- | --- |
| **What** | Generated HTML research reports, one per run. |
| **When written** | [render/html.py](../social_research_probe/render/html.py) `write_html_report`. |
| **Where read** | User browser. |
| **Who writes** | The render step. |
| **Why** | The user-facing deliverable. |
| **Format** | Self-contained HTML, UTF-8. |
| **Footprint** | 50–200 KB per report. |
| **Safe to delete** | Yes — you lose historical reports. |

## Cache key schema

Cache keys are deterministic `SHA-256` hashes of:

1. A **stage tag** (`fetch`, `hydrate`, `transcript`, `summary`, `corroboration`).
2. The **canonical input** for that stage (topic string, URL, claim text + sorted backend list).

This lets cache hits survive minor orchestration changes as long as the
semantic inputs are unchanged. TTLs are defined per sub-cache in
[utils/pipeline_cache.py](../social_research_probe/utils/pipeline_cache.py).

## `SRP_DATA_DIR` override

Every reader and writer resolves the data-dir via this env var first,
falling back to `~/.social-research-probe/`. Tests use this to redirect
everything to a `tmp_path` (`tests/conftest.py:tmp_data_dir`).

## `SRP_DISABLE_CACHE` semantics

Setting this to `"1"` makes every `pipeline_cache.get_json` return `None`
(simulating a cache miss) and every `set_json` no-op. This is the safe
way to force a fresh run without touching the on-disk cache state.

## `.gitignore` implications

If you symlink this directory inside a repo (e.g. for sharing a cache
snapshot), make sure the following are git-ignored:

- `secrets.toml` — API keys, never commit.
- `cache/` — can leak internal queries.
- `reports/` — may include titles/transcripts you didn't mean to share.

`charts/`, `topics.json`, `purposes.json`, and `config.toml` are
generally safe to commit, but double-check before pushing.
