# Charts

[Home](README.md) → Charts

Every `srp research` run renders up to 10 PNG charts saved to `~/.social-research-probe/charts/`. This page explains what each chart shows, how to read it, and what to look for.

---

## Where to find the charts

### In the HTML report (recommended)

All charts are embedded directly in the HTML report as inline images. Open the report in any browser — no separate files needed:

```
~/.social-research-probe/reports/<topic>-youtube-<YYYYMMDD-HHMMSS>.html
```

The terminal prints the exact path after each run:
```
[srp] HTML report: file:///Users/<you>/.social-research-probe/reports/ai-safety-youtube-20260420-183000.html
```

### As standalone PNGs

Each chart is also saved as an individual PNG file:

```
~/.social-research-probe/charts/
├── overall_score_bar.png
├── overall_score_by_rank_line.png
├── overall_score_histogram.png
├── trust_vs_opportunity_regression.png
├── trust_vs_trend_regression.png
├── trust_vs_opportunity_scatter.png
├── trust_vs_trend_scatter.png
├── feature_correlations_heatmap.png
├── overall_by_rank_residuals.png
└── top5_summary_table.png
```

Section 8 of the Markdown summary lists the full path to each PNG and a short caption.

---

## File persistence

**Charts (PNGs) are overwritten on every run.** Chart filenames are fixed (e.g. `overall_score_bar.png`). Each new research run replaces the previous charts in `~/.social-research-probe/charts/`. If you want to keep charts from a specific run, copy them out of that directory or rely on the HTML report, which embeds the charts at the time they were generated.

**HTML reports accumulate and are never deleted.** Each report gets a unique filename based on the topic, platform, and timestamp:
```
<topic-slug>-<platform>-<YYYYMMDD-HHMMSS>.html
```
For example:
```
~/.social-research-probe/reports/
├── ai-safety-youtube-20260420-183000.html
├── ai-safety-youtube-20260421-091500.html   ← second run, same topic
└── climate-tech-youtube-20260420-200000.html
```
Old reports are preserved indefinitely. To free disk space, delete reports manually from `~/.social-research-probe/reports/`.

---

## Chart reference

> All sample charts below use randomly generated data with 15 videos to illustrate what each chart looks like. Your actual charts will reflect real research results.

### Overall Score Bar Chart

**File:** `overall_score_bar.png`

**What it shows:** A horizontal bar for each video, sorted by overall score from highest (top) to lowest (bottom). Bar length represents the composite score (0–1 scale).

**How to read it:** The longer the bar, the higher the video ranked. A steep step-down between the first and second bars means one video is a clear standout. Bars of similar length mean the top results are closely matched.

**What to look for:** Large gaps between adjacent bars indicate natural quality tiers. If all bars are roughly the same length, the scoring did not find strong differentiation — consider widening your search with a different purpose.

![Sample overall score bar chart](images/overall_score_bar.png)

---

### Score Rank Decay Line Chart

**File:** `overall_score_by_rank_line.png`

**What it shows:** A line connecting each video's rank position (x-axis: 1st, 2nd, 3rd…) to its overall score (y-axis).

**How to read it:** A steep early drop followed by a flat tail is the most common pattern — it means the top 2–3 videos are notably better than the rest. A gradual slope means quality decreases slowly and uniformly across the dataset.

**What to look for:** A sharp cliff between rank 5 and rank 6 confirms that the top-5 enrichment budget is well-targeted. A flat line across all ranks suggests you may want to widen `max_items` to find more differentiated content.

![Sample score rank decay line chart](images/overall_score_by_rank_line.png)

---

### Overall Score Histogram

**File:** `overall_score_histogram.png`

**What it shows:** The distribution of overall scores across all fetched videos, divided into bins. Each bar represents how many videos fell in a score range.

**How to read it:** A right-skewed histogram (most bars on the left, long tail to the right) means most videos scored low with a few high-quality outliers. A symmetric, bell-shaped histogram means results are evenly distributed around an average quality level.

**What to look for:** If the histogram is bimodal (two peaks), there are two distinct quality tiers — credible sources and low-quality sources — which is useful to know when interpreting the top-5 selection.

![Sample overall score histogram](images/overall_score_histogram.png)

---

### Trust vs Opportunity Regression Scatter

**File:** `trust_vs_opportunity_regression.png`

**What it shows:** Each video as a point plotted by trust score (x-axis) vs opportunity score (y-axis), with a fitted regression line showing the trend.

**How to read it:** If the regression line slopes upward, credible channels also have high engagement opportunity on this topic. A downward slope means credible channels have lower opportunity — established sources may be saturating the topic, leaving room for newcomers.

**What to look for:** Points far above the regression line are high-opportunity, high-trust videos that stand out on both dimensions — the best candidates for deep analysis. Points below the line are sources with credibility but low engagement, suggesting specialist or niche content.

![Sample trust vs opportunity regression scatter](images/trust_vs_opportunity_regression.png)

---

### Trust vs Trend Regression Scatter

**File:** `trust_vs_trend_regression.png`

**What it shows:** Same as the trust vs opportunity chart but with trend score (view velocity) on the y-axis.

**How to read it:** A positive slope means credible channels are also trending on this topic. A negative or flat slope means viral content is coming from less-established sources, which is common on fast-moving topics where speed matters more than track record.

**What to look for:** A cluster of high-trust, high-trend points indicates authoritative sources that are gaining momentum — strong candidates for the top-5. Points with high trend but low trust are viral but unverified; treat their claims with extra scrutiny.

![Sample trust vs trend regression scatter](images/trust_vs_trend_regression.png)

---

### Trust vs Opportunity Scatter (raw)

**File:** `trust_vs_opportunity_scatter.png`

**What it shows:** The same data as the regression scatter but without the fitted line. Used to see the raw point distribution without the regression imposing a visual trend.

**How to read it:** Look for clusters, gaps, and outliers. A tight cluster in the bottom-left means most content is low-trust and low-opportunity. Isolated points in the top-right are rare high-quality finds.

![Sample trust vs opportunity scatter](images/trust_vs_opportunity_scatter.png)

---

### Trust vs Trend Scatter (raw)

**File:** `trust_vs_trend_scatter.png`

**What it shows:** Raw scatter of trust vs trend without a fitted line.

**How to read it:** Same as the trust vs opportunity scatter but for trend dynamics. Useful for identifying videos that are spiking in views (high trend) regardless of their channel credibility.

![Sample trust vs trend scatter](images/trust_vs_trend_scatter.png)

---

### Feature Correlation Heatmap

**File:** `feature_correlations_heatmap.png`

**What it shows:** A colour grid where each cell represents the Pearson correlation between two of the seven features: trust, trend, opportunity, overall score, view velocity, engagement ratio, and age in days. Darker colours indicate stronger correlations (positive or negative).

**How to read it:** Each cell is labelled with the correlation coefficient (−1 to +1). Values above 0.7 are strongly positively correlated; values below −0.7 are strongly negatively correlated; values near 0 are independent.

**What to look for:**
- A high trust–overall correlation (> 0.8) means channel credibility is the dominant driver of ranking on this topic.
- A negative age–trend correlation means newer videos are trending faster — the topic is accelerating.
- A high engagement–opportunity correlation is expected and confirms the scoring is internally consistent.

![Sample feature correlation heatmap](images/feature_correlations.png)

---

### Regression Residuals Plot

**File:** `overall_by_rank_residuals.png`

**What it shows:** The difference between each video's actual overall score and the score predicted by the rank-vs-score OLS regression. Points above the zero line scored higher than the regression predicted; points below scored lower.

**How to read it:** Most points should cluster near zero. Points far above the line are positive outliers — videos that outperformed their rank position. Points far below are underperformers that ranked high despite a lower-than-predicted score.

**What to look for:** A large positive outlier at a low rank (e.g. rank 15) suggests a hidden gem that the scoring placed low but whose quality exceeds its rank — worth investigating manually.

![Sample regression residuals plot](images/overall_by_rank_residuals.png)

---

### Top-10 Summary Table

**File:** `top5_summary_table.png`

**What it shows:** A formatted table of the top 10 scored videos with columns for rank, channel name (truncated to 25 characters), trust score, trend score, opportunity score, and overall score.

**How to read it:** This is a quick reference for the scores of each item. Use it alongside the report's Section 3 (Top Items) which includes the video title and transcript summary.

**What to look for:** Entries where trust is high but trend is low are authoritative but not currently viral — good candidates for "under the radar" expert commentary. Entries where trend is high but trust is low are viral but unverified — proceed with critical scrutiny.

![Sample top-10 summary table](images/top5_summary_table.png)

---

## Charts are not rendered when there are no results

If a research run returns zero items (e.g. the YouTube API key is misconfigured or the query returns nothing), no charts are generated and Section 8 shows `_(no charts rendered)_`.

---

## See also

- [Statistics](statistics.md) — the models behind the chart data
- [Usage Guide](usage.md) — how to control how many videos are fetched
- [Installation](installation.md) — configuring your API key
