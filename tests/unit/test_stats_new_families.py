"""Tests for the new stats families: normality, polynomial, nonparametric, bootstrap, hypothesis."""

from __future__ import annotations

from social_research_probe.stats import (
    bootstrap,
    hypothesis_tests,
    nonparametric,
    normality,
    polynomial_regression,
)


class TestNormality:
    def test_empty_series_returns_empty(self):
        assert normality.run([], label="x") == []

    def test_too_few_points_returns_empty(self):
        assert normality.run([1.0, 2.0, 3.0]) == []

    def test_zero_variance_returns_empty(self):
        assert normality.run([5.0, 5.0, 5.0, 5.0]) == []

    def test_symmetric_data(self):
        out = normality.run([1.0, 2.0, 3.0, 4.0, 5.0], label="x")
        caps = " ".join(r.caption for r in out)
        assert "Skewness" in caps
        assert "approximately symmetric" in caps

    def test_right_skewed_data(self):
        out = normality.run([1.0, 1.0, 1.0, 1.0, 10.0], label="x")
        caps = " ".join(r.caption for r in out)
        assert "right-skewed" in caps or "heavy-tailed" in caps

    def test_left_skewed_data(self):
        out = normality.run([1.0, 10.0, 10.0, 10.0, 10.0], label="x")
        caps = " ".join(r.caption for r in out)
        assert "left-skewed" in caps

    def test_light_tailed_data(self):
        out = normality.run([1.0, 2.0, 2.0, 2.0, 3.0], label="x")
        caps = " ".join(r.caption for r in out)
        assert "light-tailed" in caps or "near-normal" in caps


class TestPolynomialRegression:
    def test_too_few_points_returns_empty(self):
        assert polynomial_regression.run([1.0, 2.0], [1.0, 4.0], degree=2) == []

    def test_zero_degree_returns_empty(self):
        assert (
            polynomial_regression.run([1.0, 2.0, 3.0, 4.0], [1.0, 4.0, 9.0, 16.0], degree=0) == []
        )

    def test_perfect_quadratic_fit(self):
        x = [0.0, 1.0, 2.0, 3.0, 4.0]
        y = [xv * xv for xv in x]
        out = polynomial_regression.run(x, y, label="sq", degree=2)
        r2 = next(r for r in out if "r_squared" in r.name)
        assert r2.value > 0.999

    def test_fit_coefficients_for_viz(self):
        coeffs = polynomial_regression.fit_coefficients(
            [0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 4.0, 9.0], 2
        )
        assert coeffs is not None
        assert abs(coeffs[2] - 1.0) < 1e-9

    def test_fit_coefficients_too_few_returns_none(self):
        assert polynomial_regression.fit_coefficients([1.0, 2.0], [1.0, 4.0], 2) is None

    def test_collinear_matrix_returns_empty(self):
        assert polynomial_regression.run([1.0, 1.0, 1.0, 1.0], [1.0, 2.0, 3.0, 4.0], degree=2) == []


class TestNonparametric:
    def test_spearman_too_few_points(self):
        assert nonparametric.run_spearman([1.0], [2.0]) == []

    def test_spearman_perfect_monotone(self):
        out = nonparametric.run_spearman([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
        assert abs(out[0].value - 1.0) < 1e-9

    def test_spearman_zero_variance(self):
        out = nonparametric.run_spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])
        assert out[0].value == 0.0

    def test_mann_whitney_empty_groups(self):
        assert nonparametric.run_mann_whitney([], [1.0]) == []
        assert nonparametric.run_mann_whitney([1.0], []) == []

    def test_mann_whitney_separated_groups(self):
        out = nonparametric.run_mann_whitney([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
        assert out and "Mann-Whitney" in out[0].caption

    def test_mann_whitney_tied_groups(self):
        out = nonparametric.run_mann_whitney([1.0, 1.0], [1.0, 1.0])
        assert out and "U=" in out[0].caption


class TestBootstrap:
    def test_too_small_sample_returns_empty(self):
        assert bootstrap.run([1.0]) == []

    def test_returns_ci_bounds_surrounding_mean(self):
        out = bootstrap.run([1.0, 2.0, 3.0, 4.0, 5.0], iterations=500, seed=1)
        by_name = {r.name: r.value for r in out}
        assert by_name["bootstrap_ci_lower_values"] <= by_name["bootstrap_mean_values"]
        assert by_name["bootstrap_mean_values"] <= by_name["bootstrap_ci_upper_values"]

    def test_resample_means_exposed_for_viz(self):
        samples = bootstrap.resample_means([1.0, 2.0, 3.0], iterations=20, seed=1)
        assert len(samples) == 20

    def test_percentile_empty_returns_zero(self):
        assert bootstrap._percentile([], 0.5) == 0.0


class TestHypothesisTests:
    def test_welch_t_too_few_points(self):
        assert hypothesis_tests.run_welch_t([1.0], [2.0]) == []

    def test_welch_t_zero_variance_both(self):
        assert hypothesis_tests.run_welch_t([5.0, 5.0], [5.0, 5.0]) == []

    def test_welch_t_different_means(self):
        out = hypothesis_tests.run_welch_t([1.0, 2.0, 3.0], [10.0, 11.0, 12.0])
        assert out and "t=" in out[0].caption

    def test_anova_too_few_groups(self):
        assert hypothesis_tests.run_anova([[1.0, 2.0]]) == []

    def test_anova_insufficient_per_group(self):
        assert hypothesis_tests.run_anova([[1.0], [2.0]]) == []

    def test_anova_zero_within_variance(self):
        out = hypothesis_tests.run_anova([[1.0, 1.0], [1.0, 1.0]])
        assert out and "F=0" in out[0].caption

    def test_anova_distinct_groups(self):
        out = hypothesis_tests.run_anova(
            [[1.0, 2.0, 3.0], [10.0, 11.0, 12.0], [100.0, 101.0, 102.0]]
        )
        assert out and "F=" in out[0].caption

    def test_kruskal_wallis_too_few_groups(self):
        assert hypothesis_tests.run_kruskal_wallis([[1.0]]) == []

    def test_kruskal_wallis_empty_group(self):
        assert hypothesis_tests.run_kruskal_wallis([[1.0], []]) == []

    def test_kruskal_wallis_distinct_groups(self):
        out = hypothesis_tests.run_kruskal_wallis([[1.0, 2.0], [10.0, 20.0], [100.0, 200.0]])
        assert out and "H=" in out[0].caption

    def test_chi_square_too_few_rows(self):
        assert hypothesis_tests.run_chi_square([[1, 2]]) == []

    def test_chi_square_mismatched_cols(self):
        assert hypothesis_tests.run_chi_square([[1, 2], [1, 2, 3]]) == []

    def test_chi_square_all_zeros(self):
        assert hypothesis_tests.run_chi_square([[0, 0], [0, 0]]) == []

    def test_chi_square_real_table(self):
        out = hypothesis_tests.run_chi_square([[10, 20], [30, 40]])
        assert out and "χ²=" in out[0].caption


def test_normality_exact_light_tailed_verdict():
    """Directly probe the _kurt_verdict helper's light-tail branch (kurt < -1)."""
    from social_research_probe.stats.normality import _kurt_verdict

    assert "light-tailed" in _kurt_verdict(-2.0)


def test_chi_square_zero_expected_cell_is_skipped():
    """Table where a marginal is zero — expected cell is zero so contribution is skipped."""
    from social_research_probe.stats.hypothesis_tests import run_chi_square

    # Row 1 is all zeros, so row 1 x col 0 expected = 0 x col_total / grand = 0
    out = run_chi_square([[0, 0], [1, 1]])
    assert out and "χ²=" in out[0].caption


def test_normality_heavy_tailed_verdict():
    from social_research_probe.stats.normality import _kurt_verdict

    assert "heavy-tailed" in _kurt_verdict(2.0)
