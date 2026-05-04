[Back to docs index](README.md)


# Security

![Security boundaries](diagrams/security-boundaries.svg)

The project stores local config, secrets, cache, reports, exports, and SQLite data under the active data directory. External calls happen only through configured technologies and runner CLIs.

## Secrets

Secrets belong in `secrets.toml` or `SRP_*` environment variables. `commands/config.py` writes `secrets.toml` with `0600` permissions and warns if the file is group- or world-readable.

Do not put secrets in prompts, reports, CSV exports, Markdown files, or committed config examples.

## What Can Leave The Machine

| Boundary | Data sent |
| --- | --- |
| YouTube Data API | Search topic and video/channel IDs. |
| Transcript/media fetch | Video URLs or IDs. |
| LLM runner CLI | Prompt text, transcripts or surrogates, structured task schema. |
| Corroboration providers | Claim text and search query text. |
| Voicebox | Narration text and playback request data. |

## Report Sharing

HTML reports, exports, and SQLite rows can include source titles, URLs, comments, claims, summaries, and operator notes. Review them before sharing outside the project.
