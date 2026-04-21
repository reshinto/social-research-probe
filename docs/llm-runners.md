[Home](README.md) → LLM Runners

# LLM Runners

`srp` can call an LLM at several points in the research pipeline to turn raw transcript text into readable prose, classify free-form queries, and evaluate whether web sources support or contradict a claim. This page explains what runners are, what they do, how to pick one, and exactly what breaks when none is configured.

---

## What LLM runners are

A runner is a thin adapter that sends a text prompt to one LLM provider and returns the parsed response. The pipeline never calls a provider directly. Instead it asks the registry for the configured runner by name, and the runner handles the subprocess invocation, response parsing, and error surfacing.

Every runner implements two methods:

- `health_check()` — returns `True` when the binary or env var is present and usable.
- `run(prompt, schema=None)` — sends the prompt and returns a parsed `dict`.

New providers can be added by subclassing `LLMRunner` and decorating the class with `@register`. No pipeline code changes are needed.

---

## What runners are used for

| Pipeline stage | Where it happens | What the LLM produces |
|---|---|---|
| Transcript summarisation | Enrich stage, top-ranked videos | 100-word prose summary of the transcript |
| Section 10 — Compiled Synthesis | Synthesis stage | Structured synthesis across all enriched evidence |
| Section 11 — Opportunity Analysis | Synthesis stage | Structured opportunity analysis |
| Natural-language query classification | CLI entry point, before research begins | `topic`, `purpose_name`, and `purpose_method` derived from the free-form query |
| Claim extraction and corroboration | Corroboration host, top-N videos | Per-claim verdict: `supported`, `refuted`, or `inconclusive`, plus a confidence score and reasoning |
| Topic/purpose suggestion | `classify_query`, persisted to data dir | New topic and purpose names when none match the query |

---

## You install the CLIs yourself

`srp` does **not** bundle any LLM or call any LLM API directly. Every runner is a thin wrapper around a **separate CLI tool you install on your own machine**:

- `gemini` — from [Gemini CLI releases](https://github.com/google-gemini/gemini-cli) (npm / brew / binary).
- `claude` — from Anthropic's Claude Code CLI (`npm install -g @anthropic-ai/claude-code`).
- `codex` — from OpenAI's Codex CLI.
- `local` — any binary of your choice (Ollama wrapper, llamafile, etc.) pointed at by `SRP_LOCAL_LLM_BIN`.

`srp` does not ship any credentials and does not authenticate anything on your behalf. You log in once through the CLI (browser OAuth for Gemini and Claude, API key for Codex, nothing for `local`), then set `llm.runner`. If the CLI is missing or unauthenticated at run time, `health_check()` fails and `srp` falls back to the next runner (or skips the LLM stage entirely, if none is healthy).

---

## Supported runners

| Runner | Default model | When to use | What you must configure |
|---|---|---|---|
| `gemini` ⭐ | `gemini-2.5-pro` | **Recommended default.** Free tier, browser-auth, no API key on disk. Also powers free `llm_search` corroboration. | `gemini` CLI installed (`npm install -g @google/gemini-cli`) + `gemini auth login` (browser OAuth) |
| `claude` | Anthropic Claude (Sonnet by default) | Best prose quality when you already pay for Claude. | `claude` CLI installed and authenticated (`npm install -g @anthropic-ai/claude-code && claude auth`) |
| `codex` | `gpt-4o` | OpenAI-based; strong JSON structure | `codex` CLI installed; OpenAI API key configured in the CLI |
| `local` | `llama3.1:8b` (configurable) | Air-gapped environments; no API fees; needs capable hardware | `SRP_LOCAL_LLM_BIN` env var pointing to the binary (e.g. an Ollama wrapper); binary must accept prompt via stdin and return JSON to stdout |
| `none` | — | Explicitly disable all LLM features | Nothing — this is the default; the pipeline runs but skips all LLM stages |

### Why Gemini CLI is the recommended default

![LLM runner decision tree](diagrams/runner_choice.svg)


Most `srp` users choose Gemini as their primary runner for four reasons:

1. **Free tier covers typical research loads.** `srp` only calls the LLM for top-N per-item summaries (default 5) and one synthesis pass. Token usage is bounded, not per-item-quadratic.
2. **Browser OAuth — no API key stored anywhere.** The Gemini CLI handles token refresh internally. `srp` never touches a Gemini key; there is no `gemini_api_key` to leak.
3. **One install, two roles.** The same `gemini` binary powers the `llm_search` corroboration backend ([corroboration.md](corroboration.md)), so you get both per-item summaries and free web-search corroboration with zero extra setup.
4. **Direct media URL ingestion.** Gemini is the only runner today that implements `summarize_media()` — it can summarise a YouTube URL without `srp` downloading the transcript first. When `media_url_summary_enabled = true` (the default), this cuts wall-clock time and local CPU.

If you already pay for Claude and want the prose quality, `claude` is a strong second choice. If you run offline, `local` with a capable model works but quality varies. If you prefer not to use an LLM at all, `none` is fully supported: the CLI keeps sections 10–11 as placeholders and disables runner-backed search/classification, while the Claude Code skill can still use the host model for skill-only language work.

---

## Capability matrix

`srp` follows a **no-single-LLM-per-service** rule: every LLM-backed service
dispatches through the runner abstraction rather than hard-coding a provider.
Runners advertise capabilities via ClassVar flags; services check those flags
and skip gracefully when a capability is absent.

| Capability | Class flag | Gemini | Claude | Codex | Local |
|---|---|---|---|---|---|
| Structured JSON prompt (`run`) | *(implicit)* | ✅ | ✅ | ✅ | ✅ |
| Plain-text prompt | *(implicit)* | ✅ | ✅ | ✅ | ✅ |
| Direct media URL summary | `supports_media_url` | ✅ | — | — | — |
| Agentic web search | `supports_agentic_search` | ✅ `--google-search` | ✅ `web_search` tool | ✅ `--search` flag | ❌ raises `CapabilityUnavailable` |

**Consequence for the `llm_search` corroboration backend:** the implementation routes through
`get_runner(config.llm_runner).agentic_search(...)`. If you switch
`llm_runner` from `gemini` to `claude` or `codex`, corroboration search
automatically uses that runner's native web-search tool. Switching to
`local` makes the backend report `health_check() = False` and the host
skips it cleanly. See [docs/corroboration.md](corroboration.md) for the
full flow and [docs/diagrams/src/corroboration-runner-agnostic.mmd](diagrams/src/corroboration-runner-agnostic.mmd)
for the diagram.

---

## How the ensemble works

### Single-provider mode

When `llm.runner` is set to `claude`, `gemini`, `codex`, or `local`, that provider is used for every LLM call. If the provider fails (non-zero exit, timeout, or non-JSON response), `srp` falls back to the remaining providers in priority order (`claude → gemini → codex`) for free-text prompts. Structured JSON calls (corroboration, query classification) do the same: they try each healthy runner in order until one succeeds.

### Ensemble mode

When no explicit single provider is configured, free-text prompts (summarisation and synthesis) are fanned out to all three cloud providers concurrently via `asyncio.gather`. After all three respond, the highest-priority available provider synthesises the responses into one combined answer. This produces richer output at the cost of calling multiple APIs per prompt.

### Fallback chain (structured calls)

For structured JSON calls the runner order is `[preferred, claude, gemini, codex, local]` with the preferred runner moved to the front. Each runner is health-checked before it is tried. Runners that fail `health_check()` are skipped silently. If every runner fails, a `ValidationError` is raised and the operation is aborted with an error message.

### Failure behaviour

- A runner that times out (default 60 seconds) is killed and treated as failed.
- A runner that returns non-JSON stdout raises `AdapterError`, which is caught and treated as a failure so the next runner can be tried.
- Free-text ensemble falls back to the best single response if all synthesis attempts also fail.
- Structured calls (corroboration, NL classification) raise `ValidationError` if all runners are exhausted, which surfaces as a CLI error.

---

## Configuration

### Set the runner

```bash
srp config set llm.runner claude    # Anthropic Claude CLI
srp config set llm.runner gemini    # Google Gemini CLI
srp config set llm.runner codex     # OpenAI Codex CLI
srp config set llm.runner local     # Local binary via SRP_LOCAL_LLM_BIN
srp config set llm.runner none      # Disable LLM entirely (default)
```

### Per-runner settings

Each provider has a nested settings block in `~/.social-research-probe/config.toml`:

```toml
[llm]
runner = "claude"
timeout_seconds = 60

[llm.claude]
model = "sonnet"
extra_flags = []

[llm.gemini]
model = "gemini-2.5-pro"
extra_flags = []

[llm.codex]
binary = "codex"
model = "gpt-4o"
extra_flags = []

[llm.local]
binary = "ollama"
model = "llama3.1:8b"
extra_flags = []
```

All fields have defaults. Only set what you need to override.

### Local runner setup

The `local` runner shells out to any binary you specify. The binary must:
1. Accept the prompt on stdin.
2. Return a JSON object on stdout.
3. Accept an optional `--schema <json>` flag (used for structured calls; ignored if the binary does not support it).

```bash
export SRP_LOCAL_LLM_BIN=/usr/local/bin/my-ollama-wrapper
srp config set llm.runner local
```

---

## What changes in CLI mode without a runner

When `llm.runner = none` (the default) the pipeline still fetches, scores, and statistically analyses videos. The following are skipped or replaced with placeholder text:

| Feature | What you see |
|---|---|
| Per-video transcript summaries | Runner-written summaries are replaced by transcript- or description-derived fallback text when possible |
| Report section 10 — Compiled Synthesis | `_(LLM synthesis unavailable — runner disabled or all runners failed; see terminal logs)_` |
| Report section 11 — Opportunity Analysis | Same placeholder as section 10 |
| Corroboration (when `corroboration.backend = llm_search`) | Skipped when the runner is `none` or lacks agentic search; otherwise uses the runner's native web-search tool |
| Natural-language query mode | `srp research "who is winning the LLM benchmarks race?"` exits with an error: `cannot classify query: llm.runner is disabled` |

The YouTube fetch, scoring, statistical models (regression, Bayesian linear, bootstrap, k-means, PCA, Kaplan–Meier, and the others), and charts are all unaffected.

In the Claude Code skill, `llm.runner = none` does **not** disable the host model. The skill can still classify a free-form research request, summarise sections 1–9 inline, and draft sections 10–11 from the packet.

---

## How to verify

After setting a runner, run:

```bash
srp config show
```

With a runner configured you will see:

```json
{
  "llm": {
    "runner": "claude",
    "timeout_seconds": 60,
    "claude": { "model": "sonnet", "extra_flags": [] },
    ...
  },
  ...
}
```

With no runner configured (default):

```json
{
  "llm": {
    "runner": "none",
    "timeout_seconds": 60,
    ...
  },
  ...
}
```

To confirm the binary is reachable, run a single-video research with a short topic — if the transcript summary appears in the output the runner is working. If LLM sections show placeholder text, check that the CLI binary is installed and authenticated.

---

## Natural-language query mode

When `llm.runner` is set to any provider other than `none`, you can pass a free-form question to the CLI `srp research` command instead of an explicit topic and purpose:

```bash
srp research "who is winning the LLM benchmarks race?"
srp research "what are researchers saying about model collapse?"
```

`srp` sends the query to the configured runner (falling back through `claude → gemini → codex → local`) along with your existing topic and purpose names. The LLM returns a structured JSON object with three fields: `topic`, `purpose_name`, and `purpose_method`. If any of those are new, they are persisted to your data directory automatically, then research proceeds exactly as if you had typed `srp research <topic> <purpose>`.

If `llm.runner = none`, the command exits immediately with:

```
cannot classify query: llm.runner is disabled.
Provide explicit topic+purpose or set llm.runner in srp config.
```

This restriction is CLI-only. In the Claude Code skill, the host model can classify the free-form request first and then call the explicit `srp research <topic> <purpose>` form.

---

## See also

- [Installation](installation.md) — step-by-step setup including CLI authentication
- [Usage Guide](usage.md) — run your first research and read the output
- [Corroboration](corroboration.md) — how claim corroboration uses the runner
