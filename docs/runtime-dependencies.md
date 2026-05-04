[Back to docs index](README.md)


# Runtime Dependencies

The canonical dependency list is in `pyproject.toml`.

| Dependency | Source use |
| --- | --- |
| `jsonschema` | State validation. |
| `rapidfuzz` | Duplicate detection for topics and purposes. |
| `google-api-python-client` | YouTube Data API calls. |
| `yt-dlp` | Media fallback path. |
| `youtube-transcript-api` | Transcript fetching. |
| `matplotlib` | PNG chart rendering. |
| `openai-whisper` | Local transcription fallback. |
| `httpx` | HTTP providers such as search/corroboration integrations. |

Dev dependencies are in `[project.optional-dependencies].dev` and include pytest, coverage, asyncio test support, xdist, Hypothesis, Ruff, respx, and vulture.

External runner CLIs are not Python dependencies. They are invoked through subprocess adapters when configured and enabled.
