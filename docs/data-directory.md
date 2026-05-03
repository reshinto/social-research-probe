[Back to docs index](README.md)


# Data Directory

The data directory is the local root for state and generated artifacts. `resolve_data_dir()` selects it from `--data-dir`, `SRP_DATA_DIR`, `.skill-data/`, or `~/.social-research-probe/`.

![Cache layout](diagrams/cache-layout.svg)

## Files And Directories

| Path | Writer |
| --- | --- |
| `config.toml` | `srp config set`, `srp setup`, manual editing. |
| `secrets.toml` | `srp config set-secret`; mode should be `0600`. |
| `topics.json` | Topic commands in `commands/*topics.py`. |
| `purposes.json` | Purpose commands in `commands/*purposes.py`. |
| `pending_suggestions.json` | Suggestion workflow commands. |
| `cache/technologies/<name>/` | `BaseTechnology._cached_execute()`. |
| `charts/*.png` | `ChartsTech`. |
| `reports/*.html` | HTML report renderer. |
| `reports/*-sources.csv` | Export package. |
| `reports/*-comments.csv` | Export package. |
| `reports/*-claims.csv` | Export package. |
| `reports/*-narratives.csv` | Export package. |
| `reports/*-methodology.md` | Export package. |
| `reports/*-run_summary.json` | Export package. |
| `srp.db` | SQLite persistence technology. |

## Cache Behavior

`BaseTechnology` caches successful non-`None` outputs unless `cacheable = False`, the stage disables that technology cache, or `SRP_DISABLE_CACHE` is truthy. Default TTL is one day. Overrides in `pipeline_cache.py` set six-hour TTLs for `fetch`, `youtube_search`, and `corroborate`, and seven days for `narration`.

The cache value stores both `repr(input)` and `output`, so cache entries are inspectable JSON files.

## SQLite

When `[database].path` is empty, `Config.database_path` returns `<data_dir>/srp.db`. Relative database paths are resolved under the data directory; absolute paths are used as-is.

SQLite schema version is `4`. The schema stores runs, sources, source snapshots, comments, transcripts, text surrogates, warnings, artifacts, claims, claim reviews, claim notes, narrative clusters, narrative claims, and narrative sources.
