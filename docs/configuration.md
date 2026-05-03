[Back to docs index](README.md)

# Configuration

![Configuration lifecycle](diagrams/config_lifecycle.svg)

Configuration starts with `DEFAULT_CONFIG` in `social_research_probe/config.py`, then merges `config.toml` from the active data directory. Secrets are separate and are read from environment variables or `secrets.toml`.

## Data Directory Resolution

The active data directory is resolved before commands run:

1. `--data-dir PATH`
2. `SRP_DATA_DIR`
3. `.skill-data` in the current working directory, only if that directory already exists
4. `~/.social-research-probe`

Use `srp config path` to see the active `config.toml` and `secrets.toml` paths.

## Main Sections

| Section | Controls |
| --- | --- |
| `[llm]` | Runner name, timeout, and runner-specific CLI flags. |
| `[llm.claude]`, `[llm.gemini]`, `[llm.codex]`, `[llm.local]` | Runner binary/flag settings used by subprocess adapters. |
| `[corroboration]` | Provider mode and claim caps. |
| `[platforms.youtube]` | YouTube search recency, max results, top-N enrichment, comments, claims, narratives, and export options. |
| `[scoring.weights]` | Optional global weights for `trust`, `trend`, and `opportunity`. |
| `[stages.youtube]` | Whole-stage gates. |
| `[services.youtube.*]` | Service gates and service-level options, including source classification provider. |
| `[services.corroborate]`, `[services.enrich]`, `[services.persistence]` | Compatibility/service gates still read by commands and service selection. |
| `[technologies]` | Concrete provider, renderer, algorithm, runner, and persistence gates. |
| `[tunables]` | Summary divergence threshold and per-item summary word target. |
| `[debug]` | Runtime logging gates. |
| `[voicebox]` | Optional Voicebox profile and API base URL. |
| `[database]` | SQLite enablement, path, and text-persistence policy. |

## Stage Gates

The current YouTube stage gates are:

```toml
[stages.youtube]
fetch = true
classify = true
score = true
transcript = true
stats = true
charts = true
comments = true
summary = true
claims = true
corroborate = true
narratives = true
synthesis = true
assemble = true
structured_synthesis = true
report = true
narration = true
export = true
persist = true
```

A disabled stage publishes an empty or pass-through output when downstream stages need a stable shape.

## Service And Technology Gates

A stage can run only if its stage gate allows it. Services and technologies then apply their own gates.

Examples:

```bash
srp config set llm.runner gemini
srp config set technologies.gemini true
srp config set platforms.youtube.enrich_top_n 3
srp config set technologies.tavily false
srp config set stages.youtube.persist false
```

Use the narrowest gate that matches your intent:

| Goal | Prefer |
| --- | --- |
| Skip one provider | `technologies.<provider> = false` |
| Skip a service family | `services.youtube.<group>.<service> = false` |
| Skip a whole pipeline step | `stages.youtube.<stage> = false` |
| Disable all hosted LLM text generation | `llm.runner = "none"` |
| Disable SQLite writes | `[database].enabled = false` or `stages.youtube.persist = false` |

## Secrets

Secrets are resolved by name. Environment variables win over `secrets.toml`.

| Secret | Environment variable | Used by |
| --- | --- | --- |
| `youtube_api_key` | `SRP_YOUTUBE_API_KEY` | YouTube search, metadata, and comments. |
| `brave_api_key` | `SRP_BRAVE_API_KEY` | Brave corroboration provider. |
| `exa_api_key` | `SRP_EXA_API_KEY` | Exa corroboration provider. |
| `tavily_api_key` | `SRP_TAVILY_API_KEY` | Tavily corroboration provider. |

Set secrets without echoing values in shell history:

```bash
srp config set-secret youtube_api_key
```

Or pipe from a secret manager:

```bash
printf "%s" "$SRP_YOUTUBE_API_KEY" | srp config set-secret youtube_api_key --from-stdin
```

Check what is required before a run:

```bash
srp config check-secrets --needed-for research --platform youtube --output json
```

## Runner Configuration

Hosted runner CLIs authenticate outside `srp`; `srp` only shells out to the configured binary and parses output.

```toml
[llm]
runner = "codex"
timeout_seconds = 60

[llm.codex]
binary = "codex"
extra_flags = ["--model", "gpt-5.4"]

[technologies]
codex = true
```

For a local runner, set `llm.runner = "local"`, enable `technologies.local`, and set `SRP_LOCAL_LLM_BIN` to a wrapper that reads a prompt from stdin and writes plain text to stdout.
