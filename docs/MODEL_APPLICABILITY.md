# Statistical Model Coverage Roadmap

[Home](README.md) → Model Applicability

This document catalogues **every** model family listed in the analyst's decision
tree, maps each to whether it currently runs on the `srp research` output, and
names the **specific data capture work** required to land the remaining
families. No family is marked as "not applicable" — the right answer is always
to collect the data structure it needs.

## Currently implemented

Each row runs on the default `srp research` output and contributes
`StatResult` rows into `packet.stats_summary.highlights`.

| # | Family | Module | Notes |
|---|---|---|---|
| 1 | Descriptive | `stats.descriptive` | mean, median, min, max, stdev |
| 2 | Spread | `stats.spread` | IQR, range |
| 3 | Growth | `stats.growth` | period-over-period rate |
| 4 | Outlier detection | `stats.outliers` | z-score threshold |
| 5 | Linear regression | `stats.regression` | rank → overall slope, R² |
| 6 | Correlation (Pearson) | `stats.correlation` | trust × opportunity |
| 7 | Multi-feature OLS | `stats.multi_regression` | overall ~ trust+trend+opp |
| 8 | Normality diagnostics | `stats.normality` | skewness, kurtosis, verdict |
| 9 | Polynomial regression | `stats.polynomial_regression` | deg-2, deg-3 over rank |
| 10 | Spearman rank correlation | `stats.nonparametric` | rank-based, outlier-robust |
| 11 | Mann-Whitney U | `stats.nonparametric` | top-half vs bottom-half |
| 12 | Welch's t-test | `stats.hypothesis_tests` | unequal-variance |
| 13 | One-way ANOVA | `stats.hypothesis_tests` | multi-group F |
| 14 | Kruskal-Wallis | `stats.hypothesis_tests` | nonparametric ANOVA |
| 15 | Chi-square | `stats.hypothesis_tests` | contingency tables |
| 16 | Bootstrap CI | `stats.bootstrap` | percentile method for mean |

## Next batch — runs on current snapshot with derived targets

The current run collects per-item features (`trust`, `trend`, `opportunity`,
`overall`, `view_velocity`, `engagement_ratio`, `age_days`, `subscriber_count`)
for *n=50* items by default (raised from 20). Deriving binary / categorical /
count / event targets from these lets us run many more families immediately.

| Family | Data needed | Derivation plan |
|---|---|---|
| Binary logistic regression | binary target | `is_top_5 = rank < 5`; fit `is_top_5 ~ features` |
| Multinomial logistic | 3+ category target | `source_class ∈ {primary,secondary,commentary}`; fit `class ~ features` |
| Ordinal logistic | ordered target | `rank_bucket ∈ {top5, 6-15, 16+}`; fit `bucket ~ features` |
| Poisson regression | count target | `views_count ~ engagement + age_days + subscribers` |
| Negative binomial | overdispersed count | same as Poisson, choose when dispersion > 1 |
| Gamma regression | positive skewed continuous | `views ~ features` (views is strictly positive, skewed) |
| Beta regression | proportion on (0,1) | `engagement_ratio ~ features` (engagement ∈ [0,1]) |
| PCA | multivariate numeric | 7-feature matrix → first 2 PCs (already visualised in heatmap, adds biplot) |
| Factor analysis | multivariate numeric | PCA with varimax rotation |
| k-means clustering | multivariate numeric | `k=3` over features → tier labels |
| Hierarchical clustering | multivariate numeric | agglomerative with Ward linkage → dendrogram |
| GMM clustering | multivariate numeric | soft clustering with uncertainty |
| Naive Bayes | categorical target | `source_class ~ features` |
| KNN | any target | prediction of `is_top_5` |
| Decision tree | any target | `is_top_5 ~ features` with interpretable splits |
| Random forest | any target | ensemble for predictive accuracy |
| SVM | binary target | `is_top_5 ~ features` with RBF kernel |
| Huber / robust regression | continuous target with outliers | overall ~ rank, M-estimator |
| Kaplan-Meier survival | event + time | **event** = `views > 100k`, **time** = `age_days`; censor items below threshold |
| Cox proportional hazards | event + time + covariates | same event/time, covariates = features |
| Competing risks | multiple event types | e.g. `{crossed_100k, crossed_1M}` |
| Bayesian linear regression | continuous target | conjugate prior (Normal-Inv-Gamma) |
| Latent growth curve | repeated measures | *(requires cross-run persistence — see next batch)* |

## Next-next batch — requires cross-run persistence

These need **multiple snapshots of the same video over time**. Solution: add
a SQLite store at `~/.social-research-probe/history.db` and append each run's
items. Any video seen in ≥2 runs becomes longitudinal data.

| Family | Needs |
|---|---|
| Repeated-measures ANOVA | same videos measured across ≥2 runs |
| Linear mixed-effects | videos nested within channels, ≥2 observations each |
| GEE | population-average effects across repeated measures |
| Growth curve models | video-level trajectory of views/engagement over runs |
| Panel data / fixed effects | channel-level fixed effects across multiple runs |
| ARIMA / SARIMA | daily time series of a single metric (e.g. top-1 channel's view-velocity) |
| VAR / VECM | joint time series of ≥2 metrics |
| ARCH / GARCH | volatility model of view-velocity returns |
| State-space models | Kalman filtering of channel trajectories |
| Exponential smoothing | Holt-Winters on view-velocity time series |
| Difference-in-differences | compare channels before/after a platform event (e.g. algorithm change) |
| Regression discontinuity | exploit sharp cutoffs (e.g. monetisation thresholds) |

**Implementation sketch:** `utils/history_store.py` with `append(run_id, items)`
and `load_panel(video_ids, from_date, to_date)` functions. Pipeline writes on
every run; time-series modules read from it.

## Latent / SEM batch — requires multi-indicator measurement

These need each latent construct to be measured by ≥3 observable indicators.
Current scoring collapses everything to `trust`, `trend`, `opportunity` which
are themselves composites — we'd need to expose their sub-components.

| Family | Needs |
|---|---|
| Confirmatory factor analysis (CFA) | ≥3 indicators per latent construct |
| Structural equation modelling (SEM) | CFA + path model between constructs |
| Path analysis | all variables observed, directed paths |
| Item response theory (IRT) | binary / graded response items |
| Rasch models | dichotomous items, persons × items matrix |
| Latent class analysis (LCA) | categorical observed variables |
| Latent profile analysis (LPA) | continuous observed variables |
| Multidimensional scaling (MDS) | distance matrix between items |
| Mediation analysis | X → M → Y with bootstrap SE |

**Implementation sketch:** expose `trust` sub-components from
`scoring/trust.py` (`source_class`, `channel_credibility`,
`citation_traceability`, `ai_slop_penalty`, `corroboration_score`) as
individual features. With 5+ trust indicators we can fit a CFA.

## Causal-inference batch — requires treatment assignment

These need a treatment variable that can be thought of as manipulable.

| Family | Derivation plan |
|---|---|
| Propensity-score matching | treatment = `verified`, matched on features |
| IPW | same treatment, weight by inverse propensity |
| Instrumental variables | IV = `day_of_week_uploaded` (as-if-random) |
| Difference-in-differences | pre/post algorithm change (requires time-series batch) |
| Regression discontinuity | eligibility thresholds (e.g. `subscriber_count > 100k`) |
| Synthetic control | build counterfactual channel from donor pool |

## Specialized-domain batch

| Family | Domain | What we'd add |
|---|---|---|
| SIR / SEIR compartment | epidemiology | view-diffusion as infection model |
| Case-control logistic | epidemiology | viral vs non-viral odds-ratio analysis |
| Zero-inflated Poisson | ecology | comment-counts have many zeros |
| Capture-recapture | ecology | unique-channel estimation |
| Weibull accelerated life testing | reliability | channel-survival rates |
| Tobit / Heckman selection | econometrics | censored views (shorts cap out) |
| Panel VAR | econometrics | cross-channel dynamics |
| Joint longitudinal-survival | biostatistics | videos that "die" (unlisted/removed) |

## Honest tradeoffs

- **n=50** (per current fetch) gives decent power for correlation / regression
  tests but is too small for deep nets or multi-level models with many
  random effects.
- **Single-snapshot** data fundamentally limits what survival/longitudinal
  models can say. Adding the SQLite store is low-cost; scheduling runs is
  the real commitment.
- **No ground-truth label** makes classification evaluation self-referential
  — we can train `is_top_5 ~ features` but the target is just the ranking
  we already produced, so R² will be close to 1 by construction.
- **yt-dlp rate limiting** caps how fast we can enrich with transcripts;
  large-n + transcripts per run is slow.

## Running order

1. **This PR**: families 1–16 (descriptive through bootstrap) shipped.
2. **Next PR**: derived-target batch (logistic, Poisson, PCA, clustering,
   classifiers, Kaplan-Meier, Bayesian regression).
3. **Third PR**: history store + longitudinal/time-series batch.
4. **Fourth PR**: SEM/IRT with exposed indicator sub-components.
5. **Fifth PR**: causal-inference batch.
6. **Sixth PR**: specialized domains.
