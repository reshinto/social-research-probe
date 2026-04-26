[Back to docs index](README.md)

# API Costs And Keys

![API cost map](diagrams/api-cost-map.svg)

This guide explains which parts of `srp` can cost money, which parts are local or free to start, and why some tools need API keys while Claude, Gemini, and Codex usually do not use `SRP_*` keys.

Pricing and free tiers change. The notes below reflect the public provider pages checked on 2026-04-27. Always confirm the linked provider page before running a high-volume job.

## Quick Cost Map

| Feature | Needs `SRP_*` key? | Can spend money? | What pays for it |
| --- | --- | --- | --- |
| YouTube search and metadata | Yes, `SRP_YOUTUBE_API_KEY` or `youtube_api_key` | Usually quota-based first; paid only if your Google project is configured beyond free quota | Google Cloud project quota/billing |
| YouTube transcript API | No | No direct SRP API charge | Public captions access; may be blocked or rate-limited |
| yt-dlp fallback | No | No direct SRP API charge | Local network/compute; may need browser cookies |
| Whisper fallback | No | No direct SRP API charge | Local CPU/GPU time and disk |
| Charts/statistics/scoring/cache/HTML | No | No direct API charge | Local compute |
| Voicebox narration | Usually no `SRP_*` API key | Depends on your Voicebox setup | Local Voicebox server or your own TTS setup |
| Brave corroboration | Yes, `SRP_BRAVE_API_KEY` or `brave_api_key` | Yes after included credits/free allowance | Brave Search API account |
| Exa corroboration | Yes, `SRP_EXA_API_KEY` or `exa_api_key` | Yes after free requests/credits | Exa account |
| Tavily corroboration | Yes, `SRP_TAVILY_API_KEY` or `tavily_api_key` | Yes after free monthly credits | Tavily account |
| `llm_search` corroboration | No separate SRP key | Yes if the chosen LLM runner spends paid usage | Claude/Gemini/Codex account or local model |
| Claude runner | No SRP key | Yes, depending on Claude plan/API/provider setup | Claude Code authentication outside `srp` |
| Gemini runner | No SRP key | Yes, depending on Gemini account, API key, or Vertex setup | Gemini CLI authentication outside `srp` |
| Codex runner | No SRP key | Yes, depending on ChatGPT/Codex plan or API-key usage | Codex CLI authentication outside `srp` |
| Local LLM runner | `SRP_LOCAL_LLM_BIN`, not an API key | No vendor API charge | Local machine or your own model server |

## Why Some Tools Need SRP Keys

`srp` directly calls the YouTube, Brave, Exa, and Tavily HTTP APIs. Because the project itself sends those HTTP requests, it must know the provider credential. You can provide each credential in one of two ways:

```bash
export SRP_YOUTUBE_API_KEY="..."
export SRP_BRAVE_API_KEY="..."
export SRP_EXA_API_KEY="..."
export SRP_TAVILY_API_KEY="..."
```

or store it in the active data directory:

```bash
srp config set-secret youtube_api_key
srp config set-secret brave_api_key
srp config set-secret exa_api_key
srp config set-secret tavily_api_key
```

Environment variables win over `secrets.toml`. This is useful in CI because the same data directory can be reused while secrets are injected by the shell or secret manager.

## Why Claude, Gemini, And Codex Do Not Need SRP Keys

`srp` does not call the Anthropic, Google Gemini, or OpenAI model APIs directly. It shells out to installed command-line tools:

```text
claude -p "<prompt>"
gemini -p "<prompt>"
codex exec "<prompt>"
```

Those CLIs own authentication, account selection, model selection, and billing. `srp` only checks whether the binary is available, runs the command, waits for output, and parses the response. That is why `.env.example` does not define `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY`: those names may be valid for the vendor CLIs, but SRP itself does not read them.

Enable a hosted runner only after the CLI works by itself:

```toml
[llm]
runner = "codex"

[technologies]
codex = true
```

If the CLI needs model flags, account flags, or sandbox flags, put the vendor-specific arguments in `extra_flags`. SRP removed stale `model` example keys because the old values did not change runtime behavior and could mislead users.

```toml
[llm.codex]
binary = "codex"
extra_flags = ["--model", "gpt-5.1-codex"]
```

Use the equivalent flag syntax for the specific CLI version you installed.

## How LLM Spending Happens

LLM spending is driven by how many prompts SRP sends and how much text each prompt contains. The main LLM-using areas are:

| Area | What triggers it | Cost control |
| --- | --- | --- |
| Per-item summaries | `summary = true`, `services.youtube.enriching.summary = true`, and `llm.runner != "none"` | Lower `platforms.youtube.enrich_top_n`; use cache; enable `SRP_FAST_MODE=1` |
| Structured synthesis | `structured_synthesis = true` and an enabled runner | Disable the stage or keep `llm.runner = "none"` |
| Final synthesis | `synthesis = true` and an enabled runner | Disable the stage, reduce fetched items, or use local runner |
| `llm_search` corroboration | `corroboration.provider = "llm_search"` or `auto` chooses it | Lower `max_claims_per_item` and `max_claims_per_session` |

The safest no-model configuration is:

```toml
[llm]
runner = "none"

[stages.youtube]
summary = false
synthesis = false
structured_synthesis = false
```

That still allows fetching, scoring, statistics, charts, and basic HTML report generation.

## Provider Notes

### YouTube Data API

YouTube needs `SRP_YOUTUBE_API_KEY` because SRP calls the Data API directly. Google documents a default quota allocation of 10,000 units per day for projects that enable the YouTube Data API. A search request costs 100 units, while common metadata reads such as `videos.list` and `channels.list` cost 1 unit.

This means YouTube usage is mostly controlled by search volume and pagination. `max_items = 20` normally needs fewer search pages than a large broad crawl. If you hit quota, reduce `max_items`, narrow the topic, wait for quota reset, or request additional quota in Google Cloud.

### Brave

Brave needs `SRP_BRAVE_API_KEY` because SRP calls the Brave Search API directly. Brave currently advertises free monthly credits/allowance on its Search API page and paid request pricing above that. Brave is useful as the most conventional keyword web-index signal.

### Exa

Exa needs `SRP_EXA_API_KEY`. Exa currently advertises up to 1,000 free requests per month and paid endpoint pricing above that. Exa is useful when a source discusses the same idea with different wording because it is semantic-search oriented.

### Tavily

Tavily needs `SRP_TAVILY_API_KEY`. Tavily currently documents 1,000 free API credits per month and paid plans or pay-as-you-go above that. Tavily is useful as an independent search signal and tiebreaker when other providers disagree.

### Claude

Claude runner usage goes through Claude Code. Anthropic documents multiple Claude Code authentication methods, including Claude.ai accounts, team or enterprise authentication, Console/API, and cloud providers. SRP does not know which one you chose. Cost therefore depends on the account, plan, provider, and model behind your local `claude` CLI.

### Gemini

Gemini runner usage goes through Gemini CLI. The Gemini CLI authentication docs describe Google login, Gemini API key, Vertex AI, and headless/non-interactive setups. SRP does not choose among those; it only calls the local `gemini` command. Cost depends on whether the CLI is using free quota, a paid Gemini API key, Vertex AI billing, or a subscribed Google account setup.

### Codex

Codex runner usage goes through Codex CLI. OpenAI documents ChatGPT sign-in for Codex CLI and notes that Codex usage depends on the user plan or API-key usage. Current OpenAI help also states GPT-4o is not available in Codex and that supported Codex model families should be selected through the Codex client or supported CLI/config flags.

SRP therefore treats Codex as an external CLI, not as an OpenAI SDK client. If you authenticate Codex with ChatGPT, the Codex CLI handles that. If you authenticate it with an API key, the Codex CLI handles that too.

## Recommended Setups

| Goal | Configuration |
| --- | --- |
| Cheapest learning run | Use YouTube key, keep `llm.runner = "none"`, keep corroboration low or off. |
| Balanced research | Use YouTube key, one search provider key, and one hosted LLM runner for summaries. |
| Strong claim checking | Use Brave + Exa + Tavily or `llm_search`, with `max_claims_per_session` set to a clear budget. |
| Private/local experimentation | Use YouTube only, local charts/statistics, local LLM wrapper, and no hosted search providers. |
| Fast first draft | Set `SRP_FAST_MODE=1`, reduce `enrich_top_n`, and rely on cache for later reruns. |

## Sources

- [YouTube Data API quota costs](https://developers.google.com/youtube/v3/determine_quota_cost)
- [Brave Search API pricing](https://brave.com/search/api/)
- [Exa API pricing](https://exa.ai/pricing)
- [Tavily API credits and pricing](https://docs.tavily.com/documentation/api-credits)
- [Gemini CLI authentication](https://google-gemini.github.io/gemini-cli/docs/get-started/authentication.html)
- [Claude Code authentication](https://code.claude.com/docs/en/authentication)
- [Claude API pricing](https://platform.claude.com/docs/en/docs/about-claude/pricing)
- [Codex CLI sign in with ChatGPT](https://help.openai.com/en/articles/11381614)
- [Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540)
