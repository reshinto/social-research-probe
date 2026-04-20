"""Statistical analysis across the full scored dataset."""

from __future__ import annotations

from social_research_probe.stats import (
    bayesian_linear,
    bootstrap,
    derived_targets,
    huber_regression,
    hypothesis_tests,
    kaplan_meier,
    kmeans,
    logistic_regression,
    multi_regression,
    naive_bayes,
    nonparametric,
    normality,
    pca,
    polynomial_regression,
)
from social_research_probe.stats.selector import (
    select_and_run,
    select_and_run_correlation,
)
from social_research_probe.synthesize.explain import explain as explain_stat
from social_research_probe.types import ScoredItem, StatsSummary


def _build_stats_summary(scored_items: list[ScoredItem]) -> StatsSummary:
    """Run all applicable stats analyses across the full scored dataset.

    Statistical confidence kicks in around n>=8 for moderate correlations,
    so the pipeline now passes every fetched item rather than only the
    top-5 — that lifts ``low_confidence`` to False once a real run lands.
    """
    if not scored_items:
        return {"models_run": [], "highlights": [], "low_confidence": True}
    overall = [d["scores"]["overall"] for d in scored_items]
    trust = [d["scores"]["trust"] for d in scored_items]
    opportunity = [d["scores"]["opportunity"] for d in scored_items]
    trend = [d["scores"]["trend"] for d in scored_items]
    ranks = [float(i) for i in range(len(overall))]
    results = select_and_run(overall, label="overall_score")
    results += select_and_run_correlation(
        trust, opportunity, label_a="trust", label_b="opportunity"
    )
    results += multi_regression.run(
        overall,
        {"trust": trust, "trend": trend, "opportunity": opportunity},
        label="overall",
    )
    results += normality.run(overall, label="overall_score")
    results += polynomial_regression.run(ranks, overall, label="overall", degree=2)
    results += polynomial_regression.run(ranks, overall, label="overall", degree=3)
    results += nonparametric.run_spearman(trust, opportunity, "trust", "opportunity")
    results += nonparametric.run_mann_whitney(
        overall[: len(overall) // 2],
        overall[len(overall) // 2 :],
        "top_half",
        "bottom_half",
    )
    results += hypothesis_tests.run_welch_t(
        overall[: len(overall) // 2],
        overall[len(overall) // 2 :],
        "top_half",
        "bottom_half",
    )
    results += bootstrap.run(overall, label="overall_score")
    results += _run_advanced_models(scored_items)
    models_run = _stats_models_for(len(overall))
    if len(overall) >= 2:
        models_run += ["correlation", "spearman", "mann_whitney", "welch_t"]
    if len(overall) >= 4:
        models_run += ["normality", "polynomial_deg2", "polynomial_deg3", "bootstrap"]
    if len(overall) >= 5:
        models_run += [
            "multi_regression",
            "logistic_regression",
            "kmeans",
            "pca",
            "kaplan_meier",
            "naive_bayes",
            "huber_regression",
            "bayesian_linear",
        ]
    return {
        "models_run": models_run,
        "highlights": [explain_stat(r) for r in results],
        "low_confidence": len(overall) < 8,
    }


def _run_advanced_models(scored_items: list[ScoredItem]) -> list:
    """Run batch-2 advanced models (logistic, k-means, PCA, survival, NB, Huber, Bayes).

    Each model short-circuits to an empty list when the dataset is too
    small for identifiability; the pipeline keeps running even when
    individual models decline to fit.
    """
    if len(scored_items) < 5:
        return []
    targets = derived_targets.build_targets(scored_items)
    feature_names = [
        "trust",
        "trend",
        "opportunity",
        "view_velocity",
        "engagement_ratio",
        "age_days",
        "subscribers",
    ]
    feature_cols = {name: targets[name] for name in feature_names}
    feature_matrix = [
        [targets[name][i] for name in feature_names] for i in range(len(scored_items))
    ]
    results: list = []
    results += logistic_regression.run(targets["is_top_5"], feature_cols, label="is_top_5")
    results += kmeans.run(feature_matrix, k=3, label="items")
    results += pca.run(feature_matrix, feature_names, n_components=2, label="features")
    results += kaplan_meier.run(
        targets["time_to_event_days"],
        targets["event_crossed_100k"],
        label="views>=100k",
    )
    results += naive_bayes.run(targets["is_top_5"], feature_cols, label="is_top_5")
    results += huber_regression.run(targets["rank"], targets["overall"], label="overall")
    results += bayesian_linear.run(
        targets["overall"],
        {
            "trust": targets["trust"],
            "trend": targets["trend"],
            "opportunity": targets["opportunity"],
        },
        label="overall",
    )
    return results


def _stats_models_for(n: int) -> list[str]:
    models: list[str] = []
    if n >= 1:
        models.append("descriptive")
    if n >= 2:
        models += ["spread", "regression"]
    if n >= 3:
        models += ["growth", "outliers"]
    return models
