[Back to docs index](README.md)

# Adding A Platform

![Platform contract](diagrams/add_platform_contract.svg)

A platform adapter should fetch raw items and engagement metrics, then hand them to the shared pipeline concepts. The current concrete platform is YouTube, but YouTube is not the product boundary. The architecture is meant to support additional public sources such as TikTok, Instagram, X, web search, RSS, forums, and other platforms.

The job of a platform adapter is to translate source-specific data into the internal research shape. After that translation, the shared services should be able to score, analyze, summarize, corroborate, chart, and report without caring where the item came from.

## Contract

A platform needs:

| Part | Responsibility |
| --- | --- |
| Fetch stage | Find candidate items for a topic. |
| Raw item shape | Provide id, url, title, author/channel, timestamps, metrics, excerpts. |
| Engagement metrics | Provide velocity, engagement ratio, and cross-channel repetition when available. |
| Config defaults | Add platform limits and cache TTLs. |
| Tests | Fake data, parser coverage, stage behavior, and report integration. |

The contract should be stable before adding a new source. A platform can have source-specific fields, but the shared pipeline needs a common minimum: an item id, title, URL, source name, timestamps when available, text or transcript material when available, and numeric features that can support scoring.

![Add platform flow](diagrams/add_platform_flow.svg)

## Why this boundary

The rest of the system should not know which source produced an item. Once the adapter supplies normalized items and metrics, scoring, enrichment, analysis, and reporting can stay shared.

Without this boundary, each service would grow platform-specific branches. Charting would need to know about TikTok views versus YouTube views. Corroboration would need to know platform URL formats. Synthesis would need custom logic for every source. The adapter boundary keeps those differences close to the source integration.

## Implementation checklist

| Step | What to add | What to verify |
| --- | --- | --- |
| 1 | Platform config defaults. | The platform can be enabled, limited, and cached independently. |
| 2 | Fetch adapter. | Raw API/search results become deterministic internal items. |
| 3 | Normalization helpers. | Missing source fields become safe defaults rather than crashes. |
| 4 | Pipeline registration. | `srp research PLATFORM TOPIC PURPOSES` can route to the new platform. |
| 5 | Fake data seam. | Tests can run without network access or provider credentials. |
| 6 | Report integration. | Reports identify the source platform and preserve item URLs. |

Start small. A new platform does not need every enrichment feature on day one. It should first fetch, normalize, score, and report. Transcript-like enrichment, platform-specific metrics, and richer charts can follow once the base contract is stable.
