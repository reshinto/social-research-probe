[Back to docs index](README.md)


# Statistics

![Statistics suite](diagrams/statistics-suite.svg)

Statistics are computed by `StatisticsTech`. It extracts scored items, builds target series with `utils/analyzing/targets.py`, and runs the selector for each numeric target.

## Targets

The numeric target list in source is:

```text
overall, trust, trend, opportunity, view_velocity, engagement_ratio, age_days, subscribers, views
```

## Selector Rules

`select_and_run()` adds analyses by data size:

| Data size | Analyses |
| --- | --- |
| 1+ | Descriptive statistics. |
| 2+ | Spread and linear regression over index. |
| 3+ | Growth and outlier detection. |

Correlation has a separate selector that requires two numeric series with at least two points each.

## Output Shape

Each statistic is a `StatResult` with `name`, `value`, and `caption`. The report keeps highlight captions and sets `low_confidence = True` when fewer than five items are available.

![Statistics interpretation](diagrams/statistics-interpretation.svg)

Use statistics as descriptive signals for a fetched result set, not as population-level proof.
