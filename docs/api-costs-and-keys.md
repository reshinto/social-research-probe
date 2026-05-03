[Back to docs index](README.md)

# API Costs And Keys

![API cost map](diagrams/api-cost-map.svg)

This page explains where external services can be called and how to control that work. It deliberately avoids hard-coding provider pricing because quotas, free tiers, model access, and billing rules change. Check each provider's own dashboard/docs before high-volume runs.

## Cost Map

| Area | Needs SRP-managed secret? | Can spend money or quota? | Control |
| --- | --- | --- | --- |
| YouTube search/metadata/comments | Yes: `youtube_api_key` or `SRP_YOUTUBE_API_KEY` | Yes, through Google API quota/billing rules | Lower `platforms.youtube.max_items`; disable comments; use cache. |
| Public transcript fetch | No | Usually no direct SRP-managed API charge, but can be rate-limited | Disable transcript stage/service/technology if needed. |
| `yt-dlp` and Whisper fallback | No SRP key | Local compute/network/disk cost | Disable `yt_dlp` or `whisper`; use `--no-transcripts`. |
| Scoring/statistics/charts | No | Local compute only | Always local unless chart dependencies are missing. |
| Hosted LLM runners | No SRP key; runner CLI authenticates outside SRP | Depends on the runner account and model configuration | `llm.runner = "none"` or disable runner technology gates. |
| `llm_search` corroboration | No separate SRP key | Depends on runner account/search capability | Set `corroboration.provider = "none"` or lower claim caps. |
| Brave/Exa/Tavily corroboration | Yes: provider-specific secret | Depends on provider account/quota/billing | Disable provider technology gates or set provider to `none`. |
| Voicebox narration | Usually no SRP key | Depends on local Voicebox/TTS setup | Disable `stages.youtube.narration` or audio service. |
| SQLite persistence | No | Local disk only | Disable `[database].enabled` or `stages.youtube.persist`. |

## Secrets

Set secrets through the environment:

```bash
export SRP_YOUTUBE_API_KEY="..."
export SRP_BRAVE_API_KEY="..."
export SRP_EXA_API_KEY="..."
export SRP_TAVILY_API_KEY="..."
```

Or store them in the active data directory:

```bash
srp config set-secret youtube_api_key
srp config set-secret brave_api_key
srp config set-secret exa_api_key
srp config set-secret tavily_api_key
```

Environment variables win over `secrets.toml`.

## Why Runner CLIs Do Not Use SRP Keys

`srp` shells out to local runner CLIs:

```text
claude ...
gemini ...
codex exec ...
```

Those CLIs own authentication, account selection, model selection, and billing. `srp` checks whether the binary is available, passes prompts, enforces timeouts, and parses output.

Enable a runner with both the selected runner and its technology gate:

```toml
[llm]
runner = "codex"

[technologies]
codex = true
```

Runner-specific CLI flags live under the runner section:

```toml
[llm.codex]
binary = "codex"
extra_flags = ["--model", "gpt-5.4"]
```

## LLM Cost Controls

| LLM-using area | Trigger | Control |
| --- | --- | --- |
| Natural-language research query classification | One-argument `srp research "QUERY"` form | Use explicit `TOPIC PURPOSES`. |
| Source classification LLM fallback | `services.youtube.classifying.provider = "llm"` or `"hybrid"` and unknown channel | Use `heuristic` or disable classifying technology. |
| Per-item summaries | `llm.runner != "none"` and summary gates enabled | Lower `platforms.youtube.enrich_top_n`; use cache; disable summary stage. |
| Free-form synthesis | `stages.youtube.synthesis = true` and runner enabled | Disable synthesis or set `llm.runner = "none"`. |
| Structured synthesis | `stages.youtube.structured_synthesis = true` and runner enabled | Disable structured synthesis. |
| `llm_search` corroboration | Provider is `llm_search` or auto selects it | Lower `max_claims_per_item` and `max_claims_per_session`; disable `llm_search`. |
| LLM claim extraction | `platforms.youtube.claims.use_llm = true` | Keep deterministic extraction with `use_llm = false`. |

The safest no-hosted-model profile is:

```toml
[llm]
runner = "none"

[stages.youtube]
summary = false
synthesis = false
structured_synthesis = false

[technologies]
llm_search = false
claude = false
gemini = false
codex = false
```

## Corroboration Cost Controls

Corroboration can call multiple providers per claim. Control it with:

```toml
[corroboration]
provider = "auto" # auto | none | llm_search | exa | brave | tavily
max_claims_per_item = 5
max_claims_per_session = 15
```

Set `provider = "none"` for no corroboration calls. Use an explicit provider when you want only one provider. Use `auto` when you want the service to select healthy configured providers.

## Recommended Profiles

| Goal | Settings |
| --- | --- |
| Local learning run | YouTube key, `llm.runner = "none"`, corroboration provider `none`. |
| Fast first pass | `SRP_FAST_MODE=1`, lower `enrich_top_n`, keep cache enabled. |
| Summarized report | Enable one runner and keep `enrich_top_n` small. |
| Claim-heavy review | Enable one or more corroboration providers and set explicit claim caps. |
| Sensitive project | Use a dedicated `--data-dir`, disable hosted runners/search providers, review reports before sharing. |

## Provider Links

Use provider documentation for current quota, billing, authentication, and model-access details:

- [YouTube Data API quota costs](https://developers.google.com/youtube/v3/determine_quota_cost)
- [Brave Search API](https://brave.com/search/api/)
- [Exa API](https://exa.ai/)
- [Tavily API](https://docs.tavily.com/)
- [Gemini CLI authentication](https://google-gemini.github.io/gemini-cli/docs/get-started/authentication.html)
- [Claude Code authentication](https://docs.anthropic.com/)
- [OpenAI Codex CLI](https://github.com/openai/codex)
