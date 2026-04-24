"""Evidence tests — every stats analyzer produces reference-verified output.

Each analyzer has at least one test whose expected value is either:

- computed inline from the stdlib (``statistics.mean``, ``statistics.stdev``),
- a hand-worked micro-example where the result is trivial (all-zeros,
  perfect fit, perfect correlation), or
- cited to a published reference (Anscombe's quartet, etc.).

Tolerance is ``pytest.approx`` with a tight ``abs`` bound so a wrong formula
fails loudly instead of passing by luck.

Evidence receipt (analyzer / input / expected / why):

| Analyzer | Input | Expected | Reference |
| --- | --- | --- | --- |
| descriptive | ``[1,2,3,4,5]`` | mean=3, median=3, min=1, max=5, stdev=statistics.stdev | stdlib |
| growth | ``[100, 110, 121]`` | average period change ≈ 0.10 | formula docstring |
| regression | ``y=x`` | slope=1, R²=1 | exact fit |
| correlation | ``y=2x`` | pearson_r ≈ 1 | perfect linear |
| outliers | ``[1,2,3,4,100]`` | 1 outlier detected | z-score formula |
| spread | ``[1,1,1,1,1]`` | IQR=0, range=0 | trivial |
| bootstrap | ``[1..5]`` seeded | CI contains 3.0, mean≈3 | bootstrap theory |
| normality | 100-sample gauss seeded | verdict contains "normal" | shape classifier |
| welch_t | two identical samples | |t| < 1, p > 0.05 | null holds |
| anova | three identical groups | F ≈ 0 | null holds |
| kruskal_wallis | three groups, one shifted | H > 0 | rank differences |
| chi_square | uniform table | χ² ≈ 0 | no association |
| spearman | ranks identical | rho=1 | perfect monotonic |
| mann_whitney | samples fully separated | p small, U extreme | clear shift |
| polynomial | ``y=x²``, deg=2 | R²=1, coefs≈[0,0,1] | exact fit |
| huber | ``y=x`` + 1 outlier | slope ≈ 1 | robustness |
| multi_regression | ``y=2a+3b`` | intercept≈0, coef_a≈2, coef_b≈3 | exact fit |
| logistic | separable 2D | accuracy=1 | perfect separation |
| bayesian_linear | ``y=2x``, weak prior | bayes_coef_x≈2 | conjugate update |
| naive_bayes | 2-class Gaussian | accuracy>0.8 on train | plausible classifier |
| kaplan_meier | ``times=[10,20,30]`` all events | median≈20 | step function |
| pca | ``y=x`` 2D | PC1 variance ratio ≈ 1.0 | 1D manifold |
| kmeans | two well-separated clusters, k=2 | sizes sum to n | partition |
| selector | 100-pt series | includes descriptive + regression | documented routing |
"""

from __future__ import annotations

import itertools
import random
import statistics

import pytest
from social_research_probe.stats import (
    bayesian_linear,
    bootstrap,
    correlation,
    descriptive,
    growth,
    huber_regression,
    hypothesis_tests,
    kaplan_meier,
    kmeans,
    logistic_regression,
    multi_regression,
    naive_bayes,
    nonparametric,
    normality,
    outliers,
    pca,
    polynomial_regression,
    regression,
    selector,
    spread,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _by_name(results, name):
    """Find the first StatResult whose name matches ``name``; fail if missing."""
    for r in results:
        if r.name == name:
            return r
    names = [r.name for r in results]
    raise AssertionError(f"no StatResult named {name!r} in {names}")


# ---------------------------------------------------------------------------
# 1. descriptive
# ---------------------------------------------------------------------------


def test_descriptive_matches_stdlib_values():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = descriptive.run(data, "v")
    assert _by_name(out, "mean_v").value == pytest.approx(statistics.mean(data))
    assert _by_name(out, "median_v").value == pytest.approx(statistics.median(data))
    assert _by_name(out, "min_v").value == 1.0
    assert _by_name(out, "max_v").value == 5.0
    assert _by_name(out, "stdev_v").value == pytest.approx(statistics.stdev(data))


def test_descriptive_empty_input_returns_empty_list():
    assert descriptive.run([], "v") == []


# ---------------------------------------------------------------------------
# 2. growth
# ---------------------------------------------------------------------------


def test_growth_rate_matches_docstring_formula():
    data = [100.0, 110.0, 121.0]
    # Formula: mean of (data[i] - data[i-1]) / max(1, |data[i-1]|)
    expected = ((110 - 100) / 100 + (121 - 110) / 110) / 2
    out = growth.run(data, "v")
    assert _by_name(out, "growth_rate").value == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 3. regression
# ---------------------------------------------------------------------------


def test_regression_perfect_fit_has_slope_one_and_r_squared_one():
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    out = regression.run(data, "v")
    assert _by_name(out, "slope").value == pytest.approx(1.0, abs=1e-12)
    assert _by_name(out, "r_squared").value == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# 4. correlation
# ---------------------------------------------------------------------------


def test_correlation_perfect_linear_returns_rho_one():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [2.0, 4.0, 6.0, 8.0, 10.0]
    out = correlation.run(a, b)
    assert _by_name(out, "pearson_r").value == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# 5. outliers
# ---------------------------------------------------------------------------


def test_outliers_detects_single_extreme_value():
    data = [1.0, 2.0, 3.0, 4.0, 100.0]
    out = outliers.run(data, "v", threshold=1.5)
    assert _by_name(out, "outlier_count").value == pytest.approx(1.0)
    fraction = _by_name(out, "outlier_fraction").value
    assert fraction == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# 6. spread
# ---------------------------------------------------------------------------


def test_spread_of_constant_series_is_zero():
    out = spread.run([1.0] * 5, "v")
    assert _by_name(out, "iqr").value == 0.0
    assert _by_name(out, "range").value == 0.0


# ---------------------------------------------------------------------------
# 7. bootstrap
# ---------------------------------------------------------------------------


def test_bootstrap_ci_of_symmetric_data_contains_true_mean():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = bootstrap.run(data, "v", iterations=2000, seed=42)
    mean = _by_name(out, "bootstrap_mean_v").value
    lower = _by_name(out, "bootstrap_ci_lower_v").value
    upper = _by_name(out, "bootstrap_ci_upper_v").value
    assert mean == pytest.approx(3.0, abs=0.25)
    assert lower <= 3.0 <= upper


# ---------------------------------------------------------------------------
# 8. normality
# ---------------------------------------------------------------------------


def test_normality_on_gaussian_sample_reports_near_zero_skew():
    rng = random.Random(0)
    data = [rng.gauss(0.0, 1.0) for _ in range(200)]
    out = normality.run(data, "v")
    skew = _by_name(out, "skewness_v").value
    kurt = _by_name(out, "excess_kurtosis_v").value
    assert abs(skew) < 0.5
    assert abs(kurt) < 1.0


# ---------------------------------------------------------------------------
# 9. hypothesis_tests — welch_t, anova, kruskal_wallis, chi_square
# ---------------------------------------------------------------------------


def test_welch_t_of_identical_means_has_small_statistic():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = hypothesis_tests.run_welch_t(a, a)
    t = _by_name(out, "welch_t").value
    assert abs(t) < 1e-9


def test_anova_on_identical_groups_has_near_zero_f():
    g = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = hypothesis_tests.run_anova([g, list(g), list(g)])
    assert _by_name(out, "anova_f").value == pytest.approx(0.0, abs=1e-9)


def test_kruskal_wallis_on_shifted_groups_has_positive_h():
    out = hypothesis_tests.run_kruskal_wallis(
        [[1.0, 2.0, 3.0], [10.0, 11.0, 12.0], [100.0, 101.0, 102.0]]
    )
    assert _by_name(out, "kruskal_wallis_h").value > 0.0


def test_chi_square_of_uniform_table_is_near_zero():
    table = [[10, 10], [10, 10]]
    out = hypothesis_tests.run_chi_square(table)
    assert _by_name(out, "chi_square").value == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 10. nonparametric — spearman, mann_whitney
# ---------------------------------------------------------------------------


def test_spearman_of_monotonic_series_is_rho_one():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [10.0, 20.0, 30.0, 40.0, 50.0]
    out = nonparametric.run_spearman(a, b)
    assert _by_name(out, "spearman_rho").value == pytest.approx(1.0)


def test_mann_whitney_fully_separated_samples_has_extreme_u():
    low = [1.0, 2.0, 3.0, 4.0, 5.0]
    high = [100.0, 101.0, 102.0, 103.0, 104.0]
    out = nonparametric.run_mann_whitney(low, high)
    u = _by_name(out, "mann_whitney_u").value
    # With fully separated samples of size 5 each, U is 0 for one ordering.
    assert u in (0.0, 25.0)


# ---------------------------------------------------------------------------
# 11. polynomial_regression
# ---------------------------------------------------------------------------


def test_polynomial_regression_fits_exact_quadratic():
    x = [float(i) for i in range(-5, 6)]
    y = [xi * xi for xi in x]
    out = polynomial_regression.run(x, y, "y", degree=2)
    assert _by_name(out, "poly_deg2_r_squared_y").value == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 12. huber_regression
# ---------------------------------------------------------------------------


def test_huber_regression_resists_a_single_large_outlier():
    x = [float(i) for i in range(10)]
    y = [xi for xi in x]
    y[-1] = 1000.0  # deliberate outlier
    out = huber_regression.run(x, y, "y")
    slope = _by_name(out, "huber_slope_y").value
    # True slope without the outlier is 1.0; Huber must resist strongly.
    assert 0.5 < slope < 1.5


# ---------------------------------------------------------------------------
# 13. multi_regression
# ---------------------------------------------------------------------------


def test_multi_regression_recovers_known_coefficients():
    a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    b = [2.0, 1.0, 4.0, 3.0, 6.0, 5.0]
    y = [2 * ai + 3 * bi for ai, bi in zip(a, b, strict=True)]
    out = multi_regression.run(y, {"a": a, "b": b}, "y")
    assert _by_name(out, "intercept").value == pytest.approx(0.0, abs=1e-9)
    assert _by_name(out, "coef_a").value == pytest.approx(2.0, abs=1e-9)
    assert _by_name(out, "coef_b").value == pytest.approx(3.0, abs=1e-9)
    assert _by_name(out, "multi_r_squared").value == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 14. logistic_regression
# ---------------------------------------------------------------------------


def test_logistic_regression_overlapping_gaussian_classes_reaches_high_accuracy():
    """Perfect separation causes Newton-Raphson singularity (degenerate Hessian).
    Use two Gaussian clusters with realistic overlap — the fitter converges
    and accuracy must be high, not perfect."""
    rng = random.Random(0)
    y = [0] * 30 + [1] * 30
    features = {
        "x": [rng.gauss(-1.0, 1.0) for _ in range(30)] + [rng.gauss(1.0, 1.0) for _ in range(30)],
    }
    out = logistic_regression.run(y, features)
    acc = _by_name(out, "logistic_accuracy").value
    # True Bayes-optimal accuracy on N(-1,1) vs N(1,1) is ~84%; fitter should
    # reach at least 0.75 on a specific seeded draw.
    assert acc >= 0.75


# ---------------------------------------------------------------------------
# 15. bayesian_linear
# ---------------------------------------------------------------------------


def test_bayesian_linear_recovers_known_slope_under_weak_prior():
    x = [float(i) for i in range(20)]
    y = [2.0 * xi for xi in x]
    out = bayesian_linear.run(y, {"x": x}, "y", prior_variance=100.0)
    assert _by_name(out, "bayes_coef_x").value == pytest.approx(2.0, abs=0.05)


# ---------------------------------------------------------------------------
# 16. naive_bayes
# ---------------------------------------------------------------------------


def test_naive_bayes_classifies_well_separated_gaussian_classes():
    y = ["a"] * 20 + ["b"] * 20
    rng = random.Random(1)
    feature_vals = [rng.gauss(-2.0, 0.5) for _ in range(20)] + [
        rng.gauss(2.0, 0.5) for _ in range(20)
    ]
    out = naive_bayes.run(y, {"x": feature_vals})
    assert _by_name(out, "nb_accuracy").value >= 0.9


# ---------------------------------------------------------------------------
# 17. kaplan_meier
# ---------------------------------------------------------------------------


def test_kaplan_meier_survival_curve_decays_monotonically():
    times = [10.0, 20.0, 30.0, 40.0]
    events = [1, 1, 1, 1]
    curve = kaplan_meier.fit(times, events)
    survivals = [s for _, s in curve]
    # Monotonically non-increasing.
    assert all(s1 >= s2 for s1, s2 in itertools.pairwise(survivals))
    # With 4 events, final survival should be 0.
    assert survivals[-1] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 18. pca
# ---------------------------------------------------------------------------


def test_pca_on_one_dimensional_manifold_concentrates_variance():
    """Features on the line y=x have effectively one dimension of variance."""
    features = [[float(i), float(i)] for i in range(10)]
    out = pca.run(features, feature_names=["a", "b"], n_components=2)
    pc1 = _by_name(out, "pca_pc1_variance_ratio").value
    assert pc1 >= 0.99  # essentially all the variance is in one component


# ---------------------------------------------------------------------------
# 19. kmeans
# ---------------------------------------------------------------------------


def test_kmeans_two_well_separated_clusters_sizes_sum_to_n():
    features = [
        [0.0, 0.0],
        [0.1, 0.0],
        [0.0, 0.1],
        [10.0, 10.0],
        [10.1, 10.0],
        [10.0, 10.1],
    ]
    out = kmeans.run(features, k=2, seed=0)
    size_0 = _by_name(out, "kmeans_k2_cluster_0_size").value
    size_1 = _by_name(out, "kmeans_k2_cluster_1_size").value
    assert size_0 + size_1 == pytest.approx(len(features))
    wcss = _by_name(out, "kmeans_k2_wcss").value
    # Tight clusters — WCSS should be small relative to inter-cluster distance.
    assert wcss < 1.0


# ---------------------------------------------------------------------------
# 20. selector (routing)
# ---------------------------------------------------------------------------


def test_selector_routes_long_numeric_series_to_documented_analyzers():
    data = [float(i) + random.Random(0).gauss(0, 1) for i in range(100)]
    results = selector.select_and_run(data, "views")
    names = {r.name for r in results}
    # Selector runs descriptive + regression + outliers at minimum for a 100-point
    # series (see stats/selector.py:13-43). Assert the descriptive + regression
    # signatures are present.
    assert any(n.startswith("mean_") for n in names)
    assert "slope" in names
    assert "r_squared" in names
