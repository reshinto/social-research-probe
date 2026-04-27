[Back to docs index](README.md)

# Model Applicability

![Model applicability](diagrams/scoring-model.svg)

The project uses lightweight statistical models where the data size supports them. It avoids pretending that a tiny top-N sample can support heavy inference.

This page explains what kind of model is appropriate for what kind of data. It is separate from [Statistics](statistics.md), which lists the actual statistics and how to interpret their output.

| Model family | Minimum useful data | Use |
| --- | --- | --- |
| Descriptive stats | 1 item | Basic center and values. |
| Spread | 2 items | Variance and range-style signals. |
| Regression over rank | 2 items | Directional score movement. |
| Growth/outliers | 3 items | Simple changes and unusual points. |
| Correlation helpers | 2 paired values | Relationship between two numeric series. |
| Chart regressions | enough rendered points | Visual relationship checks. |

Advanced modules exist under `technologies/statistics`, but the production selector chooses conservative analyses for the scored dataset.

## How to choose a model

Use descriptive statistics when you only need to summarize what was fetched. Use spread and outlier checks when you need to know whether the result set is stable or dominated by a few extreme items. Use regression over rank when you want to verify whether the ranking order produces a clear score decline. Use correlation when you want to compare two numeric signals, such as trust and overall score.

Do not use complex models just because they exist. Logistic regression, clustering, PCA, and survival analysis need enough rows to say something meaningful. On tiny result sets, they can produce numbers that look precise but mostly describe noise.

## Example decisions

| Question | Better fit | Why |
| --- | --- | --- |
| Are the top results clearly better than the rest? | Rank regression and score spread. | They directly describe score movement over ranked items. |
| Is one viral item distorting the dataset? | Median, IQR, and outlier checks. | These reveal skew better than the mean alone. |
| Do trusted sources also score high overall? | Pearson or Spearman correlation. | They compare two aligned numeric series. |
| What separates top-five items from others? | Logistic regression, if enough rows exist. | The target is binary: top-five or not. |
| Are there natural groups of items? | K-means or PCA, if enough feature rows exist. | These look at multi-feature structure rather than one score. |

The safest default is to read simple statistics first, then use advanced models only when they answer a specific question and the dataset is large enough to support them.
