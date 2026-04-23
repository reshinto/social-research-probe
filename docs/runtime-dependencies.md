# Runtime dependencies

[← Documentation hub](README.md)

This page lists every third-party library `srp` imports at runtime, where
it's used in the codebase, and why it's there. Canonical source of truth
is [`pyproject.toml`](../pyproject.toml) under `[project].dependencies`
(mirrored by [`requirements.txt`](../requirements.txt) for direct
`pip install -r requirements.txt` workflows).

> **Dev-only tools** (`pytest`, `pytest-cov`, `pytest-asyncio`,
> `pytest-xdist`, `hypothesis`, `ruff`, `respx`, `vulture`) are declared
> separately under `[project.optional-dependencies].dev` and covered in
> [testing.md](testing.md). This page is only about runtime deps that
> ship with a user install.

## Runtime library usage map

| Library | Where it's used | Why | Can we drop it? |
|---|---|---|---|
| **jsonschema** | [`state/validate.py`](../social_research_probe/state/validate.py) | Validates `topics.json` / `purposes.json` / `pending_suggestions.json` against our schemas on load. Bad state files fail loudly instead of corrupting the pipeline. | Not without losing schema validation. We could switch to `pydantic`, but the migration cost isn't justified for our schema complexity. |
| **rapidfuzz** | [`dedupe.py`](../social_research_probe/dedupe.py) | Fuzzy title matching for deduping near-duplicate YouTube results (e.g. the same video reposted with a slightly different title). Fast C-accelerated Levenshtein / token-set ratio. | Could replace with `difflib.SequenceMatcher` stdlib, but rapidfuzz is 10-100× faster on our typical 20–50 item sets. |
| **google-api-python-client** | [`platforms/youtube/fetch.py`](../social_research_probe/platforms/youtube/fetch.py) (via `googleapiclient.discovery.build`) | Calls the YouTube Data API v3 for search, video hydration, and channel hydration. The adapter wraps these calls. | Could hand-roll with `httpx` against the REST endpoints; the client gives us retries, auth, and rate-limit handling for free. |
| **youtube-transcript-api** | [`platforms/youtube/extract.py`](../social_research_probe/platforms/youtube/extract.py) | Primary transcript fetch path — pulls YouTube's public timedtext captions without needing cookies or an audio download. | This is the only free, no-auth transcript path; alternatives require either API keys (paid) or a full audio download. |
| **yt-dlp** | [`platforms/youtube/whisper_transcript.py`](../social_research_probe/platforms/youtube/whisper_transcript.py) (invoked as subprocess) + referenced from [`pipeline/enrichment.py`](../social_research_probe/pipeline/enrichment.py) | **Whisper fallback** — when a video has no public captions, we download the audio track with `yt-dlp` so Whisper can transcribe locally. | Required for the captions-missing path. Without it, those videos would get an empty transcript. |
| **openai-whisper** | [`platforms/youtube/whisper_transcript.py`](../social_research_probe/platforms/youtube/whisper_transcript.py) | Local speech-to-text model for the Whisper fallback above. Runs on CPU or GPU; model size is configurable. | Required for the captions-missing path. A cloud Whisper API would work too but incur cost + network. |
| **matplotlib** | 9 files under [`viz/`](../social_research_probe/viz/) (`bar.py`, `line.py`, `scatter.py`, `histogram.py`, `regression_scatter.py`, `residuals.py`, `heatmap.py`, `table.py`, plus the module-level lazy import in `_png_writer.py`) | Renders every chart PNG embedded in the HTML report + saved under `~/.social-research-probe/charts/`. Backend is `Agg` (no display required). | We could swap for Plotly/Bokeh but matplotlib's offline rendering and long-term stability are worth the install weight. The ASCII fallback ([`viz/ascii.py`](../social_research_probe/viz/ascii.py)) works without matplotlib. |
| **httpx** | [`corroboration/brave.py`](../social_research_probe/corroboration/brave.py), [`exa.py`](../social_research_probe/corroboration/exa.py), [`tavily.py`](../social_research_probe/corroboration/tavily.py) | Async HTTP client for the three web-search corroboration backends. Supports timeouts, retries, streaming, and — crucial for tests — the `respx` mocking library. | Required; `urllib` doesn't give us async support, and our test suite depends on `respx` which targets `httpx` specifically. |

## Related docs

- [installation.md](installation.md) — installing `srp` and its runtime deps.
- [cost-optimization.md](cost-optimization.md) — which of these deps are invoked per-research-run and how we keep invocations cheap.
- [testing.md](testing.md) — dev-only tools (pytest, ruff, respx, xdist).
- [data-directory.md](data-directory.md) — where on disk each of these writes its outputs (charts, reports, cache).
