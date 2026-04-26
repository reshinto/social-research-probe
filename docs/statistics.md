[Back to docs index](README.md)

# Statistics

![Statistics suite](diagrams/statistics-suite.svg)

Statistics are computed after the pipeline has collected, enriched, and scored
research items. The statistics service does not change the ranking. It reads the
scored items, derives aligned numeric targets, runs the automatic selector, and
returns human-readable highlight captions for reports.

The report output is intentionally descriptive. Use it to understand shape,
spread, trend, and unusual values in the result set. Do not treat it as causal
proof that one feature made a video or source perform better.

## Data used by statistics

Each scored item becomes one row. Derived target arrays keep the same row order,
so `overall[3]`, `trust[3]`, `view_velocity[3]`, and `age_days[3]` describe the
same item.

| Target | Type | How it is built | How to interpret it |
| --- | --- | --- | --- |
| `rank` | Ordinal | Zero-based index in the scored list. | Lower rank means the item appears earlier in the final ranking. |
| `is_top_n` | Binary | `1` when `rank < 5`, otherwise `0`. | Useful for models that ask what separates the top five from the rest. |
| `is_top_tenth` | Binary | `1` when the item is inside the top tenth of the list, with a minimum cutoff of two. | Useful for larger result sets where "top five" is too blunt. |
| `overall` | Continuous score | `overall_score` from the scoring stage. | The final ranking score. Higher means the item is more useful for the query. |
| `trust` | Continuous score | `trust` from the scoring stage. | Higher means stronger source/reliability signal. |
| `trend` | Continuous score | `trend` from the scoring stage. | Higher means stronger recency or momentum signal. |
| `opportunity` | Continuous score | `opportunity` from the scoring stage. | Higher means the item may be useful despite not being obvious from popularity alone. |
| `view_velocity` | Continuous feature | `features.view_velocity`. | Approximate views per day. High values mean fast audience growth. |
| `engagement_ratio` | Continuous feature | `features.engagement_ratio`. | Engagement relative to views. High values mean viewers interact more often. |
| `age_days` | Continuous feature | `features.age_days`. | Days since upload. Larger values mean older items. |
| `subscribers` | Continuous feature | `features.subscriber_count`. | Channel size. Large values can explain popularity but can also hide small-channel opportunities. |
| `views` | Count-like feature | `view_velocity * age_days`. | Estimated total views from available derived features. |
| `source_class` | Categorical | Item `source_class`, defaulting to `unknown`. | Lets classification or grouped analysis compare source types. |
| `event_crossed_100k` | Binary event | `1` when estimated `views >= 100000`. | Used for event-style analysis such as "crossed 100k views". |
| `time_to_event_days` | Event time | Same value as `age_days`. | Used with event indicators for survival-style analysis. |

The automatic report suite currently runs on these numeric targets:
`overall`, `trust`, `trend`, `opportunity`, `view_velocity`,
`engagement_ratio`, `age_days`, `subscribers`, and `views`.

## Automatic report statistics

![Statistics interpretation](diagrams/statistics-interpretation.svg)

The selector runs more statistics as the sample gets larger.

| Data size | Analyses selected |
| --- | --- |
| 1 or more values | Descriptive statistics. |
| 2 or more values | Spread and regression over result order. |
| 3 or more values | Growth and outlier checks. |

The report marks `low_confidence: true` when fewer than five scored items are
available. That does not mean the numbers are wrong. It means the sample is too
small for strong interpretation.

| Statistic | Output name | What it means | How to interpret it |
| --- | --- | --- | --- |
| Mean | `mean` | Arithmetic average. | A quick center point. Sensitive to extreme values. |
| Median | `median` | Middle value after sorting. | A robust center point. If mean is much higher than median, a few large values are pulling the average up. |
| Minimum | `min` | Smallest value. | Shows the lower edge of the result set. |
| Maximum | `max` | Largest value. | Shows the upper edge of the result set. |
| Standard deviation | `stdev` | Typical distance from the mean. | Low values mean items are clustered. High values mean the result set is mixed or volatile. |
| Interquartile range | `iqr` | Spread between the 25th and 75th percentile. | Shows the middle 50 percent of values without letting extremes dominate. |
| Range | `range` | `max - min`. | A simple full spread. Useful, but very sensitive to one unusual item. |
| Linear slope | `slope` | Best-fit change per rank step, using item order as x. | Negative `overall` slope usually means scores fall as rank increases, which is expected. Positive slope suggests later items are scoring higher than earlier items. |
| R-squared | `r_squared` | How much of the target's variation is explained by a straight line over rank. | Near `1.0` means a smooth ranking curve. Near `0.0` means rank order does not explain the metric well. |
| Average growth rate | `avg_growth_rate` | Average period-over-period percentage change between adjacent ranked items. | Positive means values tend to increase down the list. Negative means values tend to decrease. Large values can be caused by small denominators. |
| Outlier count | `outlier_count` | Count of values more than two standard deviations from the mean. | Nonzero counts point to items that deserve manual inspection. |
| Outlier fraction | `outlier_fraction` | `outlier_count / sample_size`. | A high fraction means the result set is not well represented by one central number. |

## Reading examples

Assume `overall = [0.91, 0.84, 0.82, 0.52, 0.50]`.

| Result | Interpretation |
| --- | --- |
| Mean `0.718` | The average item is moderately strong. |
| Median `0.82` | The middle item is stronger than the mean, so lower-scoring items are pulling the average down. |
| Range `0.41` | There is a wide gap between the strongest and weakest item. |
| Negative slope | Ranking order is doing its job: later items generally score lower. |
| High R-squared | The score drop is smooth rather than random. |

Assume `view_velocity = [20000, 18000, 800, 700, 650]`.

| Result | Interpretation |
| --- | --- |
| Mean much higher than median | A small number of very fast videos dominate the average. |
| High standard deviation | Velocity is volatile. Compare individual items instead of trusting one average. |
| Outlier count above zero | The fastest videos should be reviewed separately from normal results. |

## Correlation helper

The statistics package also includes a selector helper for Pearson correlation
between two numeric series.

| Statistic | Output name | What it means | How to interpret it |
| --- | --- | --- | --- |
| Pearson correlation | `pearson_r` | Linear relationship between two same-length numeric series. | `1.0` means they move together, `-1.0` means they move in opposite directions, and `0.0` means no linear relationship. |

Example: a positive correlation between `trust` and `overall` means the ranking
score tends to rise when the trust score rises. It does not prove trust caused
the rank by itself, because `overall` can include multiple scoring components.

## Available advanced modules

These modules exist in `social_research_probe/technologies/statistics/`. They
are available building blocks for deeper analysis, tests, or future report
features. The current statistics report service does not automatically run all
of them on every pipeline result.

| Module | What it returns | When to use it | How to interpret it |
| --- | --- | --- | --- |
| `bootstrap` | Bootstrap mean and confidence interval bounds. | When the sample is small or skewed and a normal-theory interval would be fragile. | Narrow intervals mean the mean is stable. Wide intervals mean more data is needed. |
| `normality` | Skewness, excess kurtosis, and a normality verdict. | Before relying on statistics that assume roughly normal data. | Skew shows left/right imbalance. High kurtosis means heavy tails or sharp peaks. |
| `hypothesis_tests.run_welch_t` | Welch t statistic, degrees of freedom, and mean difference. | Compare two numeric groups with unequal variance. | Larger absolute t values suggest stronger group separation. |
| `hypothesis_tests.run_anova` | One-way ANOVA F statistic. | Compare means across three or more groups. | Larger F means between-group differences are large relative to within-group noise. |
| `hypothesis_tests.run_kruskal_wallis` | Kruskal-Wallis H statistic. | Compare groups when rank-based nonparametric analysis is safer. | Larger H means group distributions are more separated. |
| `hypothesis_tests.run_chi_square` | Chi-square statistic and degrees of freedom. | Test association in a categorical contingency table. | Larger chi-square means observed counts differ more from independent expectations. |
| `nonparametric.run_spearman` | Spearman rank correlation. | Compare monotonic relationships when raw values are nonlinear or outlier-heavy. | Positive rho means ranks rise together. Negative rho means one rank rises as the other falls. |
| `nonparametric.run_mann_whitney` | Mann-Whitney U and z approximation. | Compare two groups without assuming normal distributions. | A small U means one group tends to rank above the other. |
| `multi_regression` | Intercept, feature coefficients, R-squared, and adjusted R-squared. | Explain a continuous target with multiple numeric features. | Coefficients show feature direction while holding other features in the model. Adjusted R-squared penalizes extra features. |
| `bayesian_linear` | Posterior coefficient means, credible intervals, and residual variance. | When coefficient uncertainty matters, not just point estimates. | A credible interval crossing zero means the feature direction is uncertain. |
| `huber_regression` | Robust intercept, slope, and R-squared. | Fit a line when outliers would distort ordinary least squares. | Compare with OLS; a large difference means outliers are influencing the simple fit. |
| `polynomial_regression` | Polynomial R-squared and leading coefficient. | Detect curved relationships, such as a sharp drop after the first few ranks. | Higher R-squared than linear regression means a curve explains the pattern better. |
| `logistic_regression` | Intercept, feature coefficients, odds ratios, pseudo R-squared, and training accuracy. | Predict binary targets such as `is_top_n` or `event_crossed_100k`. | Positive coefficients increase the odds of the event; negative coefficients lower them. |
| `naive_bayes` | Class priors and training accuracy. | Build a simple classifier from numeric features and categorical labels. | Priors show class balance. Accuracy shows in-sample classification quality. |
| `kmeans` | Within-cluster sum of squares and cluster sizes. | Group items into feature-similar tiers without labels. | Lower within-cluster sum of squares means tighter clusters. Very uneven cluster sizes may indicate one dominant group plus niche outliers. |
| `pca` | Variance explained by each principal component and top loadings. | Compress many related features into fewer dimensions. | A high first-component variance ratio means one combined axis explains much of the feature movement. |
| `kaplan_meier` | Median survival and survival at a configured horizon. | Estimate time-to-event behavior, such as time until crossing a view threshold. | Survival `S(t)` is the estimated fraction that has not had the event by time `t`. |

## Practical interpretation rules

Prefer medians and IQR when popularity metrics are skewed. YouTube view and
engagement data often have a long tail, so one viral item can distort the mean,
range, and standard deviation.

Treat rank-based regressions as quality checks for the result ordering. A clean
`overall` ranking should usually show a downward slope over rank. Other targets
do not have to follow rank; for example, `opportunity` may intentionally surface
lower-popularity items.

Use outliers as review prompts, not automatic errors. An outlier can be a bad
data point, a genuinely important item, or a sign that the query found multiple
types of content.

For fewer than five items, read every number as a rough summary. A single added
or removed item can change the mean, slope, standard deviation, and outlier
status.
