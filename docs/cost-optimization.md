[Back to docs index](README.md)


# Cost Optimization

![Cost flow](diagrams/cost_flow.svg)

Cost is controlled by limiting when provider or runner technologies execute.

## Lowest-Cost Profile

```toml
[llm]
runner = "none"

[stages.youtube]
summary = false
corroborate = false
narration = false

[platforms.youtube]
max_items = 10
enrich_top_n = 3
```

## Targeted Profile

Keep scoring, statistics, charts, comments, claims, export, and persistence enabled. Enable one runner only for summary and synthesis after confirming the fetch and scoring path works.

## Corroboration Profile

Use `corroboration.max_claims_per_item` and `corroboration.max_claims_per_session` to cap provider calls. Prefer checking fewer high-value claims from top-ranked items over checking every extracted sentence.

## Cache Control

Use cache for normal work. Set `SRP_DISABLE_CACHE=1` only for benchmarking, forced refreshes, or tests that need to prove an adapter executed.
