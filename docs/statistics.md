# Statistical Models

[Home](README.md) → Statistical Models

`srp` runs up to 15+ statistical models on every research run. This page explains what each model measures, when it fires, and how to interpret the output in your report.

---

## Why statistics?

YouTube search results are noisy. A video with 10 million views might be viral clickbait; a video with 50,000 views from a specialist channel might be the most credible source on the topic. Statistics help you go beyond surface metrics and understand the *structure* of the dataset:

- Are the scores clustered or spread out? (Is there a clear winner, or are results roughly equal?)
- Does high trust predict high overall score? (Are credible sources also being rewarded by the scoring?)
- Is there an unusual outlier that warrants extra attention?
- Are results statistically separable into meaningful groups?

The statistical highlights appear in **Section 7** of the report. Each is phrased in plain English by the synthesis layer.

---

## Which models run and when

Models are gated by dataset size. Small runs (e.g. `max_items = 5`) skip models that require more data points.

| Minimum items | Models enabled |
|---|---|
| 1 | Descriptive statistics |
| 2 | Spread, OLS regression, correlation, Spearman, Mann–Whitney U, Welch's t-test |
| 3 | Growth rate, outlier detection |
| 4 | Normality test, polynomial regression (degree 2 & 3), bootstrap confidence intervals |
| 5+ | All of the above plus: multi-regression, logistic regression, k-means clustering, PCA, Kaplan–Meier survival, Naive Bayes, Huber regression, Bayesian linear regression |

Low-confidence mode is flagged when `n < 8`. The report's Section 7 will note this so you know to treat the statistics as indicative rather than conclusive.

---

## Model reference

### Descriptive statistics

**What it measures:** Mean, median, standard deviation, min, and max of the overall score.

**When it runs:** Always (n ≥ 1).

**How to interpret:** The mean tells you the average quality of results. A high standard deviation means the results are very uneven — some standout videos and many poor ones. A low standard deviation means most videos are similar in quality.

**Example finding:** "Mean overall score: 0.62. Std dev: 0.21 — moderate spread, suggesting a few high-quality sources among average results."

---

### Spread analysis

**What it measures:** Interquartile range (IQR), skewness, and kurtosis of the overall score distribution.

**When it runs:** n ≥ 2.

**How to interpret:** High skewness (> 1) means most results cluster at the low end with a few outliers at the top — common when one viral channel dominates. Kurtosis indicates how extreme the tail outliers are. A wide IQR means the middle 50% of results are very diverse.

---

### OLS linear regression (rank vs score)

**What it measures:** Fits a straight line to the relationship between a video's rank position (1st, 2nd, 3rd…) and its overall score. The slope tells you how steeply quality drops off down the list.

**When it runs:** n ≥ 2.

**How to interpret:** A steep negative slope means the top-ranked video is significantly better than the others. A shallow slope means the results are roughly equal in quality and the ranking is less decisive.

---

### Correlation (Pearson)

**What it measures:** Linear correlation between trust score and opportunity score across all items.

**When it runs:** n ≥ 2.

**How to interpret:** A strong positive correlation (+0.7 or above) means channels with high credibility also have high engagement opportunity — credible sources are also accessible. A near-zero correlation means trust and opportunity are independent, and you may need to choose between authoritative sources and engaging ones.

---

### Spearman rank correlation

**What it measures:** Same as Pearson correlation but uses ranks instead of raw values, making it robust to outliers and non-linear relationships.

**When it runs:** n ≥ 2.

**How to interpret:** Compare with the Pearson result. If Spearman is much higher than Pearson, the relationship is monotonic but not linear (e.g. exponential). If they are similar, the relationship is roughly linear.

---

### Mann–Whitney U test

**What it measures:** Tests whether the top half of results (by rank) has significantly different overall scores from the bottom half — without assuming a normal distribution.

**When it runs:** n ≥ 2.

**How to interpret:** A statistically significant result (p < 0.05) means there is a real quality gap between the top and bottom halves of your results. An insignificant result means the divide between "good" and "bad" results is not statistically meaningful — the dataset may be uniformly mediocre or uniformly good.

---

### Welch's t-test

**What it measures:** Same hypothesis as Mann–Whitney but assumes normally distributed scores. Compares means between top and bottom halves.

**When it runs:** n ≥ 2.

**How to interpret:** Use alongside the normality test. If the normality test passes, Welch's t-test is reliable. If the normality test fails, trust Mann–Whitney instead.

---

### Normality test (Shapiro–Wilk)

**What it measures:** Tests whether the overall scores follow a normal (bell-curve) distribution.

**When it runs:** n ≥ 4.

**How to interpret:** If the test passes (scores are normal), parametric tests like Welch's t are valid. If it fails, the distribution is skewed or has heavy tails — use the non-parametric results (Spearman, Mann–Whitney) instead.

---

### Polynomial regression (degree 2 & 3)

**What it measures:** Fits a curve (quadratic or cubic) to the rank vs score relationship. Captures non-linear score decay patterns.

**When it runs:** n ≥ 4.

**How to interpret:** A good quadratic fit means quality drops sharply in the top few results, then flattens — a typical "power law" content distribution. If the cubic fit is significantly better than quadratic, there is a more complex structure (e.g. a cluster of mid-tier results above a floor).

---

### Bootstrap confidence intervals

**What it measures:** Resamples the dataset 1,000 times to estimate a 95% confidence interval for the mean overall score. Does not assume any distribution.

**When it runs:** n ≥ 4.

**How to interpret:** A tight confidence interval (e.g. [0.58, 0.65]) means the mean is stable and the dataset is consistent. A wide interval means the mean is sensitive to which specific videos appeared in this run — results would likely vary significantly on a re-run.

---

### Multiple regression

**What it measures:** Fits a linear model predicting the overall score from all three sub-scores (trust, trend, opportunity) simultaneously. The coefficients show which sub-score drives the overall score most.

**When it runs:** n ≥ 5.

**How to interpret:** A high trust coefficient means credibility dominates the ranking on this topic. A high trend coefficient means view velocity is the main driver. Use this to understand what kind of content your scoring is rewarding for the current topic and purpose.

---

### Logistic regression

**What it measures:** Predicts whether an item will rank in the top 5 based on its seven features (trust, trend, opportunity, view velocity, engagement ratio, age in days, subscriber count).

**When it runs:** n ≥ 5.

**How to interpret:** The feature with the highest coefficient is the strongest predictor of top-5 inclusion. This is more actionable than multiple regression when you want to understand "what makes a video stand out" rather than "what drives the overall score."

---

### K-means clustering (k=3)

**What it measures:** Groups all scored items into 3 clusters based on their seven-feature vectors. Each cluster represents a distinct type of video in the dataset.

**When it runs:** n ≥ 5.

**How to interpret:** Typical clusters are "credible established channels," "new viral content," and "niche low-engagement sources." The cluster labels are not fixed — look at the centroid values to characterise each group. A cluster with very few members is an outlier group.

---

### PCA (Principal Component Analysis)

**What it measures:** Reduces the seven features to two principal components that capture the most variance. Used to visualise the structure of the dataset in the scatter chart.

**When it runs:** n ≥ 5.

**How to interpret:** The first principal component typically separates high-overall from low-overall items. The second often separates trust-dominated from trend-dominated items. If PC1 explains > 70% of variance, the dataset has a single dominant dimension and one score (likely trust) is driving everything.

---

### Kaplan–Meier survival analysis

**What it measures:** Treats the time for a video to reach 100,000 views as a "survival time" and estimates the probability of reaching that milestone at each age (days since publish).

**When it runs:** n ≥ 5.

**How to interpret:** A steep early drop in the survival curve means most videos hit 100k views quickly (viral content). A flat curve means most videos never reach 100k — content on this topic has limited viral potential. The median survival time (50% mark on the curve) tells you how long it typically takes for a breakout video to become visible.

---

### Naive Bayes

**What it measures:** A probabilistic classifier that predicts top-5 membership using the seven features, treating each feature independently. Provides a baseline accuracy score.

**When it runs:** n ≥ 5.

**How to interpret:** Accuracy above 70% means the features are good predictors of top-5 inclusion. Low accuracy (below 60%) suggests that top-5 status is not well-explained by the available features — other factors (e.g. timing, thumbnails) may matter more.

---

### Huber regression

**What it measures:** A robust linear regression that is less sensitive to outliers than OLS. Fits rank vs score with downweighted influence for unusual items.

**When it runs:** n ≥ 5.

**How to interpret:** Compare with the OLS regression result. If the Huber slope is much less steep than OLS, there is at least one outlier video inflating the apparent quality gap. The Huber result is the more reliable summary of the typical rank-score relationship.

---

### Bayesian linear regression

**What it measures:** Fits a linear model from trust, trend, and opportunity to the overall score using Bayesian estimation. Reports the posterior mean and a credible interval for each coefficient.

**When it runs:** n ≥ 5.

**How to interpret:** The credible interval tells you how uncertain the coefficient estimate is given this data size. A narrow interval (e.g. trust: 0.35 ± 0.04) means the result is reliable. A wide interval means you need more data before drawing conclusions about which sub-score matters most.

---

## Low-confidence mode

When fewer than 8 items are scored, the report flags `low_confidence: true` in the statistics section. All models still run (subject to their individual minimum-n thresholds), but the findings should be treated as directional rather than statistically rigorous.

To get reliable statistics, set `max_items` to at least 20 (the default). Below 8 results, standard errors are large and p-values unreliable.

---

## See also

- [Charts](charts.md) — visual representations of these statistical results
- [Usage Guide](usage.md) — how to control how many videos are fetched
- [model-applicability.md](model-applicability.md) — which LLM models are recommended for statistical explanation
