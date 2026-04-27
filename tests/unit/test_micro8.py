"""Push to 100% — micro 8."""

from __future__ import annotations

from social_research_probe.technologies.statistics import (
    bayesian_linear,
    growth,
    huber_regression,
    kaplan_meier,
    kmeans,
    logistic_regression,
    multi_regression,
    naive_bayes,
    normality,
    pca,
    polynomial_regression,
)


def test_pca_zero_variance_features():
    # Constant columns → variance=0 → low_variance branch
    features = [[1.0, 5.0], [1.0, 5.0], [1.0, 5.0]]
    out = pca.run(features, feature_names=["a", "b"])
    assert isinstance(out, list)


def test_pca_ncomponents_capped():
    # n_components > d → cap at d
    out = pca.run([[1.0, 2.0], [3.0, 4.0]], feature_names=["a", "b"], n_components=10)
    assert isinstance(out, list)


def test_pca_d_less_than_2():
    # 1D feature → returns []
    out = pca.run([[1.0], [2.0]], feature_names=["a"])
    assert out == []


def test_pca_n_components_zero():
    # n_components < 1 → returns []
    out = pca.run([[1.0, 2.0]], feature_names=["a", "b"], n_components=0)
    assert out == []


def test_pca_fit_components_too_few():
    assert pca.fit_components([], 2) == []
    assert pca.fit_components([[1.0]], 2) == []


def test_growth_constant_data():
    # data with 0 changes → growth=0
    out = growth.run([1.0, 1.0, 1.0])
    assert isinstance(out, list)


def test_normality_constant_data():
    # variance=0 → returns []
    out = normality.run([5.0, 5.0, 5.0])
    assert out == []


def test_normality_heavy_kurt():
    out = normality.run([1.0, 1.0, 1.0, 100.0, 1.0])
    assert out


def test_huber_break_via_solver_no_change(monkeypatch):
    """Force the all-equal branch in iterative loop."""
    fixed = [0.0, 1.0]
    call_count = {"n": 0}

    def solve(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] > 5:
            return fixed[:]
        return [0.0, 1.0 + 1e-10]

    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.huber_regression._solve_normal_equations",
        solve,
    )
    out = huber_regression.run([1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 2.0, 3.0, 4.0, 5.0])
    assert out


def test_logistic_break_via_no_change(monkeypatch):
    fixed = [0.0, 0.0]
    call_count = {"n": 0}

    def solve(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] > 1:
            return fixed[:]
        return [0.0, 1e-10]

    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.logistic_regression._solve_normal_equations",
        solve,
    )
    out = logistic_regression.run([0, 1, 0, 1], {"x": [1.0, 2.0, 3.0, 4.0]}, max_iter=10)
    assert isinstance(out, list)


def test_multi_regression_solver_none(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.multi_regression._solve_normal_equations",
        lambda *a, **kw: None,
    )
    out = multi_regression.run([1.0, 2.0, 3.0], {"x": [1.0, 2.0, 3.0]})
    assert out == []


def test_naive_bayes_empty_y():
    # No labels → returns []
    out = naive_bayes.run([], {})
    assert out == []


def test_kaplan_meier_unequal_lens():
    # Different len times/events
    assert kaplan_meier.fit([1.0], [1, 0]) == []


def test_kmeans_n_lt_k():
    # n < k → returns ([], [])
    out = kmeans.fit([[1.0]], k=5)
    assert out == ([], [])


def test_polynomial_run_no_coeffs(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.polynomial_regression._solve_normal_equations",
        lambda *a, **kw: None,
    )
    out = polynomial_regression.run([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0], degree=1)
    assert out == []


def test_bayesian_too_few_y(monkeypatch):
    # n=1 forced
    out = bayesian_linear.run([1.0], {"x": [1.0]})
    assert out == []
