[Back to docs index](README.md)


# LLM Runners

![Runner choice](diagrams/runner_choice.svg)

The LLM layer is adapter-based. The registry in `utils/llm/registry.py` maps runner names to classes. Concrete runner modules are imported by `ensure_runners_registered()`.

## Runner Names

| Name | Source class | Enabled by |
| --- | --- | --- |
| `claude` | `ClaudeRunner` | `llm.runner = "claude"` and `technologies.claude = true` |
| `gemini` | `GeminiRunner` | `llm.runner = "gemini"` and `technologies.gemini = true` |
| `codex` | `CodexRunner` | `llm.runner = "codex"` and `technologies.codex = true` |
| `local` | stdin/stdout wrapper through `SRP_LOCAL_LLM_BIN` | `llm.runner = "local"` and `technologies.local = true` |
| `none` | no runner | Disables LLM-dependent outputs. |

## How Calls Work

`JsonCliRunner` builds an argv list from the configured binary, base argv, extra flags, optional schema flag, and prompt. It checks whether the binary exists on `PATH`. Calls are subprocess-based and timeout through the configured LLM timeout.

`LLMService` is sequential, not concurrent. It tries the preferred runner first, then other enabled runners from the registry until one succeeds.

## What Runners Produce

Runners can support structured JSON tasks, summaries, synthesis, query classification, source classification fallback, LLM claim extraction, and runner-backed search when the concrete runner advertises that capability.

Runners should not own platform fetches, cache layout, SQLite schema, or report file paths.
