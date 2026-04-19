"""Tests for the multi-feature OLS regression module."""

from __future__ import annotations

from social_research_probe.stats import multi_regression


def test_returns_empty_when_no_data():
    assert multi_regression.run([], {}) == []


def test_returns_empty_when_features_empty():
    assert multi_regression.run([1.0, 2.0, 3.0], {}) == []


def test_returns_empty_when_n_too_small_for_features():
    # 3 samples, 2 features + intercept = 3 params → n must be > 3
    out = multi_regression.run(
        [1.0, 2.0, 3.0],
        {"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]},
    )
    assert out == []


def test_perfect_linear_fit_recovers_coefficients():
    # y = 1 + 2*a + 3*b — choose non-collinear features
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [1.0, 4.0, 9.0, 16.0, 25.0]
    y = [1.0 + 2 * ai + 3 * bi for ai, bi in zip(a, b, strict=True)]
    results = multi_regression.run(y, {"a": a, "b": b}, label="y")
    by_name = {r.name: r.value for r in results}
    assert abs(by_name["intercept"] - 1.0) < 1e-9
    assert abs(by_name["coef_a"] - 2.0) < 1e-9
    assert abs(by_name["coef_b"] - 3.0) < 1e-9
    assert abs(by_name["multi_r_squared"] - 1.0) < 1e-9


def test_singular_matrix_returns_empty():
    # collinear features → singular X^T X
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [2.0, 4.0, 6.0, 8.0, 10.0]  # b = 2a → collinear
    out = multi_regression.run([1.0, 2.0, 3.0, 4.0, 5.0], {"a": a, "b": b})
    assert out == []


def test_zero_variance_dependent_returns_zero_r_squared():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [1.0, 4.0, 9.0, 16.0, 25.0]
    y = [3.0] * 5
    results = multi_regression.run(y, {"a": a, "b": b})
    by_name = {r.name: r.value for r in results}
    assert by_name["multi_r_squared"] == 0.0
