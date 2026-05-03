[Back to docs index](README.md)

# Data Directory

![Data and cache layout](diagrams/cache-layout.svg)

The data directory is the local home for non-secret config, secrets, state, cache, chart PNGs, reports, export artifacts, and the optional SQLite database.

## Resolution

Run:

```bash
srp config path
```

The parent directory of the printed `config.toml` and `secrets.toml` paths is the active data directory.

Resolution order:

| Priority | Source | Example |
| --- | --- | --- |
| 1 | Global `--data-dir` flag | `srp --data-dir ./research-data config path` |
| 2 | `SRP_DATA_DIR` environment variable | `SRP_DATA_DIR=./research-data srp config path` |
| 3 | Local `.skill-data` directory if it already exists | `./.skill-data` |
| 4 | Home default | `~/.social-research-probe` |

Use project-local `.skill-data` for experiments that should stay with a workspace. Use the home default for a personal setup reused across many projects.

## Current Layout

```text
<data-dir>/
  config.toml
  secrets.toml
  topics.json
  purposes.json
  pending_suggestions.json
  report.md
  srp.db
  srp.db-shm
  srp.db-wal
  voicebox_profiles.json
  charts/
    overall_score_bar.png
    overall_score_by_rank_line.png
    overall_score_histogram.png
    trust_vs_opportunity_regression.png
    trust_vs_trend_regression.png
    trust_vs_opportunity_scatter.png
    trust_vs_trend_scatter.png
    feature_correlations.png
    overall_by_rank_residuals.png
    top_n_summary_table.png
  reports/
    <run-id>.html
    <run-id>-sources.csv
    <run-id>-comments.csv
    <run-id>-claims.csv
    <run-id>-narratives.csv
    <run-id>-methodology.md
    <run-id>-run_summary.json
    <run-id>.voicebox.<profile>.mp3
  cache/
    technologies/
      youtube_search/
      youtube_hydrate/
      youtube_engagement/
      youtube_transcript_api/
      yt_dlp/
      whisper/
      classifying.heuristic/
      classifying.llm/
      classifying.hybrid/
      llm.<runner>/
      claim_extractor/
      corroboration_host/
      stats_per_target/
      charts_suite/
      export_package/
```

Not every path appears in every run. Directories are created lazily when a command or technology writes them.

## What Files Mean

| Item | Created by | Meaning |
| --- | --- | --- |
| `config.toml` | `srp setup`, `srp config set`, or manual edit | Non-secret configuration merged over `DEFAULT_CONFIG`. |
| `secrets.toml` | `srp config set-secret` or setup | Local secret store with `0600` permissions. |
| `topics.json` | Topic commands | Saved topic names. |
| `purposes.json` | Purpose commands | Saved purpose definitions, evidence priorities, and scoring overrides. |
| `pending_suggestions.json` | Suggestion commands | Staged generated suggestions waiting for apply/discard. |
| `cache/technologies/<name>/*.json` | `BaseTechnology` cache wrapper | Cached technology output keyed by a hash of `repr(input)`. |
| `charts/*.png` | Chart technology | Current chart suite images for scored items. |
| `report.md` | Markdown fallback writer | Latest fallback Markdown report; later fallback writes can overwrite it. |
| `reports/<run-id>.html` | HTML report renderer | Human-readable report. |
| `reports/<run-id>-*.csv` | Export package | Machine-readable sources, comments, claims, and narratives. |
| `reports/<run-id>-methodology.md` | Export package | Methodology summary for the run. |
| `reports/<run-id>-run_summary.json` | Export package | Machine-readable run metadata and artifact paths. |
| `srp.db*` | SQLite persistence stage | Local run, source, snapshot, claim, narrative, artifact, and warning history. |
| `voicebox_profiles.json` | Report/Voicebox integration | Cached Voicebox profile metadata. |

## Cache Behavior

`BaseTechnology` handles cache for cacheable technologies. Cache entries live under `cache/technologies/<technology-name>/`.

Default TTL is one day. Current overrides:

| Technology name | TTL |
| --- | --- |
| `fetch` | 6 hours |
| `youtube_search` | 6 hours |
| `corroborate` | 6 hours |
| `narration` | 7 days |

Most current technology names use the default TTL unless listed above. Set `SRP_DISABLE_CACHE=1` to bypass reads and writes for one command:

```bash
SRP_DISABLE_CACHE=1 srp research youtube "AI safety" "latest-news"
```

Delete a targeted technology cache when you need a focused refresh:

```bash
rm -rf ~/.social-research-probe/cache/technologies/youtube_search
```

Do not delete `config.toml`, `secrets.toml`, `topics.json`, or `purposes.json` unless you intend to reset setup or saved state.

## Inspecting Outputs

```bash
srp config path
find ~/.social-research-probe -maxdepth 2 -type f
find ~/.social-research-probe/reports -maxdepth 1 -type f
find ~/.social-research-probe/charts -maxdepth 1 -type f
find ~/.social-research-probe/cache/technologies -maxdepth 2 -type d
srp db stats
```

Use the same commands with `--data-dir` for project-local state:

```bash
srp --data-dir ./.skill-data config path
find ./.skill-data -maxdepth 2 -type f
```

## Troubleshooting

| Problem | Check first |
| --- | --- |
| Config changes seem ignored | `srp config path`; you may be editing another data directory. |
| Secrets seem missing | `srp config check-secrets --needed-for research --platform youtube --output json`. |
| Charts are missing | `charts/`, `stages.youtube.charts`, `services.youtube.analyzing.charts`, and `technologies.charts_suite`. |
| HTML is missing | `reports/`, `stages.youtube.report`, `services.youtube.reporting.html`, and `--no-html`. |
| Exports are missing | HTML report path plus `stages.youtube.export` and `platforms.youtube.export.enabled`. |
| Database rows are missing | `[database].enabled`, `stages.youtube.persist`, `services.persistence.sqlite`, and `technologies.sqlite_persist`. |
| Old evidence keeps appearing | `SRP_DISABLE_CACHE=1` or delete the relevant `cache/technologies/<name>/` folder. |

## Safety

The data directory can contain topics, source URLs, cached source text, generated summaries, reports, exports, and secrets. Do not commit it unless you intentionally want to publish that data. For examples and tests, prefer small fixtures under `tests/fixtures/` instead of real run output.
