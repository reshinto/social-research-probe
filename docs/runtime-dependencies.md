[Back to docs index](README.md)

# Runtime Dependencies

![Runtime component map](diagrams/components.svg)

Runtime dependencies are intentionally small and focused. The project prefers standard-library code, narrow adapters, and external runner CLIs over installing a large SDK for every possible provider.

This matters for users because the tool should remain installable in ordinary Python environments. Heavy optional behavior, such as local transcription or external model runners, should not make the core CLI impossible to use.

| Dependency | Why it exists |
| --- | --- |
| `jsonschema` | Validates local JSON state files. |
| `rapidfuzz` | Detects duplicate or near-duplicate topics and purposes. |
| `google-api-python-client` | Talks to the YouTube Data API. |
| `yt-dlp` | Fetches media metadata/captions when needed. |
| `youtube-transcript-api` | Transcript retrieval path. |
| `matplotlib` | Renders chart PNGs. |
| `openai-whisper` | Local transcript fallback. |
| `httpx` | HTTP calls for provider integrations. |

Optional runner CLIs such as Claude, Gemini, Codex, or Ollama are not Python dependencies. They are external programs called by subprocess adapters.

## Why not one SDK per provider?

The code prefers narrow adapters and CLI boundaries where possible. That keeps install size lower and avoids coupling the core pipeline to every vendor's Python SDK.

SDKs are useful when a provider needs deep API coverage. This project usually needs a smaller contract: run a search, fetch a transcript, render a chart, or ask a runner for structured text. Keeping those integrations behind small adapters makes it easier to replace or disable one dependency without changing the whole pipeline.

## Dependency categories

| Category | Examples | Failure behavior |
| --- | --- | --- |
| Core validation and state | `jsonschema`, `rapidfuzz` | Required for normal CLI behavior. |
| Platform access | `google-api-python-client`, `yt-dlp`, `youtube-transcript-api` | Platform features may be unavailable if missing or unauthenticated. |
| Local analysis and rendering | `matplotlib`, pure Python statistics modules | Charts or analysis outputs may be skipped on renderer failure. |
| Optional local media work | `openai-whisper` | Transcript fallback may be unavailable. |
| Provider HTTP clients | `httpx` | External evidence providers depend on network and secrets. |
| Runner CLIs | Claude, Gemini, Codex, Ollama-style tools | Generated text may be absent if the runner is not installed or configured. |

When debugging dependency issues, first identify the category. A missing runner should not be treated like a broken install if the user only wants local scoring and charts.
