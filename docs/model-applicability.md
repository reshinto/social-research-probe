# Statistical Model Reference

[Home](README.md) → Statistical Model Reference

This document maps every statistical model family to its implementation module, the minimum dataset size it requires, and the data it operates on. For a guide to interpreting model output, see [Statistics](statistics.md).

---

## Currently implemented

All models below run automatically on every `srp research` output. Each contributes result rows into `packet.stats_summary.highlights`, which are rendered in Section 7 of the report.

| # | Model | Module | Min items | Input data |
|---|---|---|---|---|
| 1 | Descriptive statistics | `stats.descriptive` | 1 | Overall score |
| 2 | Spread (IQR, range) | `stats.spread` | 2 | Overall score |
| 3 | Growth rate | `stats.growth` | 3 | Overall score |
| 4 | Outlier detection | `stats.outliers` | 3 | Overall score |
| 5 | OLS linear regression | `stats.regression` | 2 | Rank → overall slope, R² |
| 6 | Pearson correlation | `stats.correlation` | 2 | Trust × opportunity |
| 7 | Multiple OLS regression | `stats.multi_regression` | 5 | Overall ~ trust + trend + opportunity |
| 8 | Normality diagnostics | `stats.normality` | 4 | Skewness, kurtosis, Shapiro–Wilk |
| 9 | Polynomial regression (deg 2 & 3) | `stats.polynomial_regression` | 4 | Rank → overall |
| 10 | Spearman rank correlation | `stats.nonparametric` | 2 | Trust × opportunity |
| 11 | Mann–Whitney U test | `stats.nonparametric` | 2 | Top half vs bottom half |
| 12 | Welch's t-test | `stats.hypothesis_tests` | 2 | Top half vs bottom half |
| 13 | Bootstrap confidence intervals | `stats.bootstrap` | 4 | Overall score (percentile method) |
| 14 | Logistic regression | `stats.logistic_regression` | 5 | is_top_5 ~ 7 features |
| 15 | K-means clustering (k=3) | `stats.kmeans` | 5 | 7-feature matrix |
| 16 | PCA | `stats.pca` | 5 | 7-feature matrix → 2 principal components |
| 17 | Kaplan–Meier survival | `stats.kaplan_meier` | 5 | Time to reach 100k views |
| 18 | Naive Bayes | `stats.naive_bayes` | 5 | is_top_5 ~ 7 features |
| 19 | Huber regression | `stats.huber_regression` | 5 | Rank → overall (outlier-robust) |
| 20 | Bayesian linear regression | `stats.bayesian_linear` | 5 | Overall ~ trust + trend + opportunity |

### The 7 features used by advanced models

Advanced models (rows 14–20) operate on a feature vector derived for each item:

| Feature | What it captures |
|---|---|
| `trust` | Channel credibility score |
| `trend` | View velocity (views per hour since publish) |
| `opportunity` | Engagement rate relative to channel size |
| `view_velocity` | Raw views per day |
| `engagement_ratio` | (likes + comments) / views |
| `age_days` | Days since the video was published |
| `subscribers` | Channel subscriber count |

---

## Planned models (not yet implemented)

These models require data structures that are not yet collected. They are documented here so contributors know what groundwork is needed.

### Requires cross-run persistence (SQLite history store)

Once a `~/.social-research-probe/history.db` store appends each run's items, any video seen in two or more runs becomes longitudinal data and the following models become available:

| Model | What it needs |
|---|---|
| Repeated-measures ANOVA | Same videos measured across ≥ 2 runs |
| Linear mixed-effects | Videos nested within channels, ≥ 2 observations |
| ARIMA / SARIMA | Daily time series of a single metric |
| Growth curve models | Video-level view trajectory over time |
| Difference-in-differences | Before/after a platform algorithm change |

### Requires exposed scoring sub-components

The trust, trend, and opportunity scores are each composites of 3–5 sub-indicators. When those sub-indicators are exposed as individual features, models that need multiple indicators per latent construct become feasible:

| Model | What it needs |
|---|---|
| Confirmatory factor analysis (CFA) | ≥ 3 indicators per latent construct |
| Structural equation modelling (SEM) | CFA + path model between constructs |
| Mediation analysis | X → M → Y with bootstrap standard errors |

---

## Tradeoffs and limitations

- **Dataset size.** Fetching 20 videos (the default) gives decent statistical power for correlation and regression but is too small for multi-level models. Set `max_items` to at least 20–50 for reliable results. Below 8 items, the report flags `low_confidence: true`.

- **Single-snapshot data.** Most models run on a single point-in-time snapshot. Survival and longitudinal models are structurally limited until the history store is built.

- **Self-referential classification.** Models that predict `is_top_5` use the pipeline's own scoring as the ground truth label. R² will be artificially high — these models reveal which features *drive the scoring*, not which features predict external quality.

- **Transcript rate-limiting.** Enriching more than ~20 items per run with transcripts is slow due to yt-dlp rate limits. Increase `max_items` for better statistical coverage, but expect longer run times.

---

## See also

- [Statistics](statistics.md) — what each model measures and how to interpret it
- [Charts](charts.md) — visualisations derived from these models
- [Usage Guide](usage.md) — how to control `max_items` and `recency_days`
