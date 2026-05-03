Files: `config.toml`, `secrets.toml` under active data dir. Secrets env override: `SRP_<SECRET_NAME_UPPER>`.

- Show merged: `srp config show`
- Paths: `srp config path`
- Set scalar/list leaf: `srp config set DOTTED.KEY VALUE`
- Set secret hidden prompt: `srp config set-secret NAME`
- Set secret stdin: `srp config set-secret NAME --from-stdin`
- Remove secret: `srp config unset-secret NAME`
- Check: `srp config check-secrets [--needed-for research] [--platform youtube] [--corroboration exa|brave|tavily] --output json`

Core keys:
- `llm.runner`: `none|claude|gemini|codex|local`
- `corroboration.provider`: `auto|none|llm_search|exa|brave|tavily`
- `platforms.youtube`: `recency_days`, `max_items`, `enrich_top_n`, `comments`, `claims`, `narratives`, `export`
- `stages.youtube`: `fetch`, `classify`, `score`, `transcript`, `summary`, `comments`, `claims`, `corroborate`, `stats`, `charts`, `narratives`, `synthesis`, `assemble`, `structured_synthesis`, `report`, `narration`, `export`, `persist`
- `services.youtube.*`: sourcing/scoring/enriching/corroborating/analyzing/synthesizing/reporting leaves
- `services.persistence.sqlite`: SQLite persistence service gate
- `technologies`: `classifying`, `youtube_api`, `youtube_transcript_api`, `whisper`, `yt_dlp`, `voicebox`, `llm_search`, `exa`, `brave`, `tavily`, `claude`, `gemini`, `codex`, `local`, `llm_ensemble`, `llm_synthesis`, `html_render`, `stats_per_target`, `charts_suite`, `scoring_compute`, `youtube_search`, `youtube_hydrate`, `youtube_engagement`, `corroboration_host`, `mac_tts`, `claim_extractor`, `narrative_clusterer`, `ai_slop_detector`, `youtube_comments`, `export_package`

Known required secrets: `youtube_api_key`; corroboration: `exa_api_key`, `brave_api_key`, `tavily_api_key`.
