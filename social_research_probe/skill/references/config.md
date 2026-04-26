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
- `platforms.youtube`: `recency_days`, `max_items`, `enrich_top_n`, cache TTLs
- `stages.youtube`: `fetch`, `score`, `transcript`, `summary`, `corroborate`, `stats`, `charts`, `synthesis`, `assemble`, `structured_synthesis`, `report`, `narration`
- `services.youtube.*`: sourcing/scoring/enriching/corroborating/analyzing/synthesizing/reporting leaves
- `technologies`: `youtube_api`, `youtube_transcript_api`, `whisper`, `yt_dlp`, `voicebox`, `claude`, `gemini`, `codex`, `local`, `llm_search`, `exa`, `brave`, `tavily`

Known required secrets: `youtube_api_key`; corroboration: `exa_api_key`, `brave_api_key`, `tavily_api_key`.
