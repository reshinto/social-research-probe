[Back to docs index](README.md)

# Corroboration

![Corroboration flow](diagrams/corroboration_flow.svg)

Corroboration checks claims from top-ranked items against external evidence. It is optional and controlled by `corroboration.provider`, service gates, technology gates, and available secrets.

The purpose is not to prove every sentence in a report. It is to reduce the risk that a generated summary or source item repeats an unsupported claim. The pipeline extracts or receives claims, sends them to a configured evidence provider, and records the provider response in the report packet so a human can inspect what was checked.

## Providers

| Provider | Secret | Notes |
| --- | --- | --- |
| `exa` | `exa_api_key` | Search API provider. |
| `brave` | `brave_api_key` | Search API provider. |
| `tavily` | `tavily_api_key` | Search API provider. |
| `llm_search` | active runner | Uses a runner's agentic search capability. |
| `none` | none | Disables corroboration. |
| `auto` | provider-specific | Tries enabled healthy providers in configured order. |

![Runner agnostic corroboration](diagrams/corroboration-runner-agnostic.svg)

## Why this design

Corroboration is separated from summarization because claim checking needs fresh external evidence, while summaries can often rely on transcript text. Separating the two keeps costs visible and lets a user disable paid search providers without disabling the whole research run.

This also keeps the report honest about evidence quality. A transcript summary can say what a source claimed. Corroboration can say whether another provider found supporting, conflicting, or missing evidence. Those are different questions and should not be merged into one opaque LLM call.

## Tradeoffs

| Choice | Benefit | Cost |
| --- | --- | --- |
| Provider fan-out | More chance of finding evidence. | More API calls and rate-limit exposure. |
| `auto` mode | Works with whatever is configured. | Results may vary across machines. |
| LLM search provider | Reuses authenticated runner CLI. | Depends on runner support for web search. |

## How to read results

Read corroboration as an evidence check, not a final verdict. A supported claim means the provider found material that appears to back it. A conflicting claim means the provider found material that pushes against it. Missing evidence means the configured providers did not find enough support in that run; it does not always mean the claim is false.

When corroboration looks weak, check the claim text first. Overly broad claims are hard to verify. Then check which provider was active, whether the provider had a valid secret, and whether `enrich_top_n` was high enough to send the relevant item through claim extraction.
