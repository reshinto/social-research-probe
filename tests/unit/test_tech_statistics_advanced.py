"""Tests for advanced tech.statistics modules."""

from __future__ import annotations

from social_research_probe.technologies.statistics import (
    bayesian_linear,
    bootstrap,
    huber_regression,
    hypothesis_tests,
    kaplan_meier,
    kmeans,
    logistic_regression,
    multi_regression,
    naive_bayes,
    nonparametric,
    pca,
    polynomial_regression,
)


class TestHypothesisTests:
    def test_welch_t_too_few(self):
        assert hypothesis_tests.run_welch_t([1.0], [1.0, 2.0]) == []

    def test_welch_t_zero_variance_both(self):
        assert hypothesis_tests.run_welch_t([1.0, 1.0], [2.0, 2.0]) == []

    def test_welch_t_basic(self):
        out = hypothesis_tests.run_welch_t([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        assert out and out[0].name == "welch_t"

    def test_anova_too_few_groups(self):
        assert hypothesis_tests.run_anova([[1.0, 2.0]]) == []

    def test_anova_undersized_group(self):
        assert hypothesis_tests.run_anova([[1.0], [2.0, 3.0]]) == []

    def test_anova_basic(self):
        out = hypothesis_tests.run_anova([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        assert out and out[0].name == "anova_f"

    def test_kruskal_too_few(self):
        assert hypothesis_tests.run_kruskal_wallis([[1.0]]) == []

    def test_kruskal_basic(self):
        out = hypothesis_tests.run_kruskal_wallis([[1.0, 2.0], [3.0, 4.0]])
        assert out and out[0].name == "kruskal_wallis_h"

    def test_chi_square_too_few_rows(self):
        assert hypothesis_tests.run_chi_square([[1, 2]]) == []

    def test_chi_square_inconsistent_cols(self):
        assert hypothesis_tests.run_chi_square([[1, 2], [3]]) == []

    def test_chi_square_zero_grand(self):
        assert hypothesis_tests.run_chi_square([[0, 0], [0, 0]]) == []

    def test_chi_square_basic(self):
        out = hypothesis_tests.run_chi_square([[10, 20], [20, 10]])
        assert out and out[0].name == "chi_square"


class TestBootstrap:
    def test_too_few(self):
        assert bootstrap.run([1.0]) == []

    def test_basic(self):
        out = bootstrap.run([1.0, 2.0, 3.0, 4.0], iterations=50)
        names = {r.name for r in out}
        assert {
            "bootstrap_mean_values",
            "bootstrap_ci_lower_values",
            "bootstrap_ci_upper_values",
        } <= names

    def test_resample_means_length(self):
        means = bootstrap.resample_means([1.0, 2.0, 3.0], iterations=10)
        assert len(means) == 10

    def test_percentile_empty(self):
        assert bootstrap._percentile([], 0.5) == 0.0

    def test_percentile_basic(self):
        assert bootstrap._percentile([1.0, 2.0, 3.0], 0.5) == 2.0


class TestNonparametric:
    def test_spearman_too_few(self):
        assert nonparametric.run_spearman([1.0], [2.0]) == []

    def test_spearman_basic(self):
        out = nonparametric.run_spearman([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
        assert out and out[0].name == "spearman_rho"

    def test_mann_whitney_empty(self):
        assert nonparametric.run_mann_whitney([], [1.0]) == []

    def test_mann_whitney_basic(self):
        out = nonparametric.run_mann_whitney([1.0, 2.0], [3.0, 4.0])
        assert out and out[0].name == "mann_whitney_u"


class TestKaplanMeier:
    def test_empty(self):
        assert kaplan_meier.run([], []) == []

    def test_basic(self):
        out = kaplan_meier.run([1.0, 2.0, 3.0, 4.0], [1, 0, 1, 1])
        assert out

    def test_fit_returns_curve(self):
        curve = kaplan_meier.fit([1.0, 2.0, 3.0], [1, 1, 1])
        assert curve

    def test_survival_at_zero(self):
        curve = kaplan_meier.fit([1.0, 2.0], [1, 1])
        assert kaplan_meier.survival_at(curve, 0.0) == 1.0


class TestKmeans:
    def test_empty(self):
        out = kmeans.run([], k=2)
        assert out == []

    def test_basic(self):
        features = [[0.0, 0.0], [0.1, 0.1], [10.0, 10.0], [10.1, 10.1]]
        out = kmeans.run(features, k=2)
        assert out

    def test_fit_returns_assignments(self):
        features = [[0.0], [0.1], [10.0], [10.1]]
        result = kmeans.fit(features, k=2, max_iter=10, seed=1)
        assert result


class TestPca:
    def test_empty(self):
        assert pca.run([], feature_names=[]) == []

    def test_basic(self):
        features = [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0]]
        out = pca.run(features, feature_names=["a", "b"])
        assert out


class TestPolynomialRegression:
    def test_too_few(self):
        assert polynomial_regression.run([1.0], [1.0]) == []

    def test_basic(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [v * v for v in x]
        out = polynomial_regression.run(x, y, degree=2)
        assert out


class TestMultiRegression:
    def test_too_few_features(self):
        assert multi_regression.run([1.0], {}) == []

    def test_basic(self):
        y = [1.0, 2.0, 3.0, 4.0]
        features = {"x": [1.0, 2.0, 3.0, 4.0]}
        out = multi_regression.run(y, features)
        assert isinstance(out, list)


class TestNaiveBayes:
    def test_empty(self):
        assert naive_bayes.run([], {}) == []

    def test_basic(self):
        y = ["a", "a", "b", "b"]
        features = {"x": [1.0, 1.1, 5.0, 5.1]}
        out = naive_bayes.run(y, features)
        assert out


class TestHuberRegression:
    def test_too_few(self):
        assert huber_regression.run([1.0], [1.0]) == []

    def test_basic(self):
        x = list(range(1, 8))
        y = [v * 2.0 + 1.0 for v in x]
        out = huber_regression.run(x, y)
        assert out


class TestBayesianLinear:
    def test_too_few(self):
        assert bayesian_linear.run([1.0], {}) == []

    def test_basic(self):
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        features = {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}
        out = bayesian_linear.run(y, features)
        assert isinstance(out, list)


class TestLogisticRegression:
    def test_too_few(self):
        assert logistic_regression.run([], {}) == []

    def test_basic(self):
        y = [0, 0, 1, 1, 1]
        features = {"x": [1.0, 1.5, 5.0, 5.5, 6.0]}
        out = logistic_regression.run(y, features, max_iter=10)
        assert isinstance(out, list)
