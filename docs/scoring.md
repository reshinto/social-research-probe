[Back to docs index](README.md)


# Scoring

![Scoring model](diagrams/scoring-model.svg)

Scoring lives in `technologies/scoring`. The service delegates to `ScoringComputeTech`, which normalizes items, aligns engagement metrics, computes component scores, and sorts by `scores.overall` descending.

## Component Scores

Trust:

```text
0.35 * source_class
+ 0.25 * channel_credibility
+ 0.15 * citation_traceability
+ 0.15 * (1 - ai_slop_penalty)
+ 0.10 * corroboration_score
```

Trend:

```text
0.40 * norm_z(view_velocity)
+ 0.20 * norm_z(engagement_ratio)
+ 0.20 * norm_z(cross_channel_repetition)
+ 0.20 * exp(-age_days / 30)
```

Opportunity:

```text
0.40 * market_gap
+ 0.30 * monetization_proxy
+ 0.20 * feasibility
+ 0.10 * novelty
```

Overall:

```text
0.45 * trust + 0.30 * trend + 0.25 * opportunity
```

All component outputs are clipped into `[0.0, 1.0]`.

## Current Signal Sources

`compute_trust()` currently uses fixed `source_class = 0.4`, `citation_traceability = 0.3`, `ai_slop_penalty = 0.0`, and `corroboration_score = 0.3`, plus subscriber-derived channel credibility. Channel credibility is `0.3` when subscriber count is missing and otherwise `min(1.0, 0.15 * log10(subscribers))`.

`compute_opportunity()` derives market gap from cross-channel repetition, monetization proxy from engagement ratio, feasibility as `0.5`, and novelty from item age.

## Weight Overrides

`resolve_scoring_weights()` applies weights in this order:

1. `DEFAULT_WEIGHTS` from `technologies/scoring/combine.py`.
2. `[scoring.weights]` from config.
3. Merged purpose `scoring_overrides`.

Only `trust`, `trend`, and `opportunity` are recognized.
