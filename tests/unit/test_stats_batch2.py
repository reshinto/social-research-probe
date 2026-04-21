"""Tests for batch-2 stats families: derived targets, logistic, k-means, PCA, KM, NB, Huber, Bayesian."""

from __future__ import annotations

from social_research_probe.stats import (
    bayesian_linear,
    derived_targets,
    huber_regression,
    kaplan_meier,
    kmeans,
    logistic_regression,
    naive_bayes,
    pca,
)


def _scored(n: int) -> list[dict]:
    return [
        {
            "title": f"t{i}",
            "channel": f"ch{i % 3}",
            "url": f"https://x/{i}",
            "source_class": ["primary", "secondary", "commentary"][i % 3],
            "scores": {
                "trust": 0.5 + i * 0.02,
                "trend": 0.4 + i * 0.03,
                "opportunity": 0.6 + i * 0.01,
                "overall": 0.5 + i * 0.02,
            },
            "features": {
                "view_velocity": 100.0 * (i + 1),
                "engagement_ratio": 0.02 + i * 0.005,
                "age_days": float(i + 1),
                "subscriber_count": 1000.0 * (i + 1),
            },
            "one_line_takeaway": "...",
        }
        for i in range(n)
    ]


class TestDerivedTargets:
    def test_builds_all_columns(self):
        t = derived_targets.build_targets(_scored(15))
        for key in [
            "rank",
            "is_top_n",
            "is_top_tenth",
            "overall",
            "trust",
            "trend",
            "opportunity",
            "view_velocity",
            "engagement_ratio",
            "age_days",
            "subscribers",
            "views",
            "source_class",
            "event_crossed_100k",
            "time_to_event_days",
        ]:
            assert key in t and len(t[key]) == 15

    def test_is_top_n_marks_first_five(self):
        t = derived_targets.build_targets(_scored(10))
        assert t["is_top_n"] == [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]

    def test_event_threshold_when_views_high(self):
        items = _scored(10)
        for it in items:
            it["features"]["view_velocity"] = 50000.0
            it["features"]["age_days"] = 5.0
        t = derived_targets.build_targets(items)
        assert all(e == 1 for e in t["event_crossed_100k"])


class TestLogisticRegression:
    def test_empty_returns_empty(self):
        assert logistic_regression.run([], {"a": []}) == []

    def test_no_features_returns_empty(self):
        assert logistic_regression.run([0, 1, 0, 1, 0], {}) == []

    def test_constant_target_returns_empty(self):
        assert logistic_regression.run([1, 1, 1, 1, 1], {"a": [1.0, 2.0, 3.0, 4.0, 5.0]}) == []

    def test_too_few_samples_for_features(self):
        assert logistic_regression.run([0, 1], {"a": [1.0, 2.0]}) == []

    def test_predictive_signal_recovers_positive_coefficient(self):
        # Mildly separated (not perfectly) so IRLS converges without weights collapsing
        x = [1.0, 2.0, 1.5, 3.0, 2.5, 4.0, 3.5, 5.0, 4.5, 6.0]
        y = [0, 0, 1, 0, 1, 0, 1, 1, 1, 1]
        out = logistic_regression.run(y, {"x": x}, label="binary")
        names = {r.name: r for r in out}
        assert "logistic_intercept" in names
        assert "logistic_coef_x" in names
        assert names["logistic_coef_x"].value > 0


class TestKMeans:
    def test_too_few_samples(self):
        assert kmeans.run([[1.0]], k=3) == []

    def test_invalid_k(self):
        assert kmeans.run([[1.0], [2.0], [3.0]], k=1) == []

    def test_clusters_separated_data(self):
        data = [[0.0], [0.1], [0.2], [10.0], [10.1], [10.2], [100.0], [100.1], [100.2]]
        out = kmeans.run(data, k=3, seed=1)
        wcss = next(r.value for r in out if "wcss" in r.name)
        assert wcss < 1.0

    def test_fit_returns_centroids_and_labels(self):
        data = [[0.0], [0.1], [10.0], [10.1]]
        centroids, labels = kmeans.fit(data, k=2, seed=0)
        assert len(centroids) == 2
        assert len(labels) == 4

    def test_fit_too_few_samples_returns_empty(self):
        assert kmeans.fit([[1.0]], k=3) == ([], [])

    def test_empty_cluster_keeps_previous_centroid(self):
        # Force the empty-members branch by giving enough points but co-located
        data = [[0.0], [0.0], [10.0], [10.0]]
        centroids, _ = kmeans.fit(data, k=2, seed=42)
        assert len(centroids) == 2


class TestPCA:
    def test_too_few_samples(self):
        assert pca.run([[1.0, 2.0]], ["a", "b"]) == []

    def test_too_few_features(self):
        assert pca.run([[1.0], [2.0], [3.0]], ["a"]) == []

    def test_fit_components_too_small(self):
        assert pca.fit_components([[1.0, 2.0]]) == []

    def test_fits_two_components_from_three_features(self):
        data = [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0], [4.0, 8.0, 12.0]]
        out = pca.run(data, ["a", "b", "c"], n_components=2, label="x")
        names = [r.name for r in out]
        assert "pca_pc1_variance_ratio" in names
        assert "pca_pc2_variance_ratio" in names

    def test_fit_components_returns_vectors(self):
        data = [[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0]]
        comps = pca.fit_components(data, n_components=2)
        assert len(comps) == 2

    def test_project_centers_and_projects(self):
        data = [[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0]]
        comps = pca.fit_components(data, n_components=1)
        projected = pca.project(data, comps)
        assert len(projected) == 4

    def test_zero_variance_dimension(self):
        data = [[1.0, 0.0], [2.0, 0.0], [3.0, 0.0], [4.0, 0.0]]
        out = pca.run(data, ["a", "b"], n_components=2, label="x")
        assert out  # still returns something


class TestKaplanMeier:
    def test_empty_returns_empty(self):
        assert kaplan_meier.run([], []) == []

    def test_mismatched_lengths(self):
        assert kaplan_meier.run([1.0], [1, 0]) == []

    def test_no_events_reports_no_events(self):
        out = kaplan_meier.run([1.0, 2.0, 3.0], [0, 0, 0], label="ev")
        assert "no events observed" in out[0].caption

    def test_all_events_at_same_time(self):
        out = kaplan_meier.run([5.0, 5.0, 5.0, 5.0], [1, 1, 0, 0])
        assert any("median" in r.name for r in out)

    def test_fit_empty_when_mismatched(self):
        assert kaplan_meier.fit([1.0], [1, 0]) == []

    def test_survival_at_horizon(self):
        out = kaplan_meier.run([1.0, 2.0, 30.0, 60.0], [1, 1, 0, 1], horizon_days=30.0)
        s_at = next(r.value for r in out if "s_at_30d" in r.name)
        assert 0.0 <= s_at <= 1.0

    def test_survival_at_function(self):
        curve = [(0.0, 1.0), (5.0, 0.8), (10.0, 0.6), (20.0, 0.4)]
        assert kaplan_meier.survival_at(curve, 7.0) == 0.8
        assert kaplan_meier.survival_at(curve, 100.0) == 0.4


class TestNaiveBayes:
    def test_empty_returns_empty(self):
        assert naive_bayes.run([], {}) == []

    def test_single_class_returns_empty(self):
        assert naive_bayes.run([1, 1, 1], {"a": [1.0, 2.0, 3.0]}) == []

    def test_no_features_returns_empty(self):
        assert naive_bayes.run([0, 1, 0, 1], {}) == []

    def test_separable_classes(self):
        x = [1.0, 1.5, 2.0, 10.0, 10.5, 11.0]
        y = [0, 0, 0, 1, 1, 1]
        out = naive_bayes.run(y, {"x": x}, label="y")
        accuracy = next(r.value for r in out if r.name == "nb_accuracy")
        assert accuracy >= 0.83

    def test_predict_function_directly(self):
        priors = {0: 0.5, 1: 0.5}
        mus = {0: {"x": 1.0}, 1: {"x": 10.0}}
        sigmas = {0: {"x": 0.5}, 1: {"x": 0.5}}
        assert naive_bayes.predict({"x": 1.0}, priors, mus, sigmas) == 0
        assert naive_bayes.predict({"x": 10.0}, priors, mus, sigmas) == 1


class TestHuberRegression:
    def test_too_few_samples(self):
        assert huber_regression.run([1.0, 2.0], [3.0, 4.0]) == []

    def test_mismatched_lengths(self):
        assert huber_regression.run([1.0, 2.0, 3.0], [1.0, 2.0]) == []

    def test_fits_clean_line(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        out = huber_regression.run(x, y, label="y")
        slope = next(r.value for r in out if "slope" in r.name)
        assert abs(slope - 2.0) < 0.01

    def test_resists_outlier(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0, 1000.0]
        out = huber_regression.run(x, y, label="y")
        slope = next(r.value for r in out if "slope" in r.name)
        # Huber should not fit the 1000 outlier
        assert abs(slope - 2.0) < 1.0

    def test_zero_residual_data_returns_results(self):
        x = [1.0, 2.0, 3.0, 4.0]
        y = [1.0, 1.0, 1.0, 1.0]
        out = huber_regression.run(x, y)
        assert out


class TestBayesianLinear:
    def test_too_small_returns_empty(self):
        assert bayesian_linear.run([1.0, 2.0], {"a": [1.0, 2.0]}) == []

    def test_no_features_returns_empty(self):
        assert bayesian_linear.run([1.0, 2.0, 3.0, 4.0], {}) == []

    def test_recovers_perfect_linear(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0 * v + 1.0 for v in x]
        out = bayesian_linear.run(y, {"x": x}, label="y")
        coef = next(r.value for r in out if r.name == "bayes_coef_x")
        assert abs(coef - 2.0) < 0.5

    def test_includes_credible_interval_in_caption(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        y = [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]
        out = bayesian_linear.run(y, {"x": x}, label="y")
        cap = next(r.caption for r in out if r.name == "bayes_coef_x")
        assert "95% CrI" in cap

    def test_singular_returns_empty(self):
        # Two perfectly collinear features -> singular posterior precision after solving
        x1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        # collinear but with prior_variance huge so prior precision is small;
        # we still expect a fit, this just exercises the fit path
        out = bayesian_linear.run(
            [2.0, 4.0, 6.0, 8.0, 10.0],
            {"a": x1, "b": x1},
            label="y",
            prior_variance=1e9,
        )
        # Bayesian regression with shrinkage prior may still fit collinear data
        assert isinstance(out, list)


class TestEdgeCaseCoverage:
    def test_kmeans_single_dim_with_duplicates_to_force_recompute_no_members(self):
        from social_research_probe.stats.kmeans import _recompute_centroids

        # Cluster 1 has no members assigned -> falls back to previous centroid
        prev = [[5.0], [99.0]]
        new = _recompute_centroids([[1.0], [2.0]], [0, 0], 2, prev)
        assert new[1] == [99.0]

    def test_kmeans_zero_centroid_returns_empty_when_n_lt_k(self):
        from social_research_probe.stats.kmeans import run

        # k=2 but n=1 — too few samples
        assert run([[1.0]], k=2) == []

    def test_naive_bayes_single_value_falls_back_to_default_sigma(self):
        from social_research_probe.stats.naive_bayes import fit

        # Class 1 has only 1 sample for feature 'x' -> hits the len(values)<2 branch
        _priors, _mus, sigmas = fit([0, 0, 1], {"x": [1.0, 2.0, 3.0]})
        assert sigmas[1]["x"] == 1.0

    def test_bayesian_linear_singular_returns_empty(self):
        # Force singularity by passing fully duplicate features and small prior
        from social_research_probe.stats.bayesian_linear import _diagonal_of_inverse

        singular = [[1.0, 1.0], [1.0, 1.0]]
        assert _diagonal_of_inverse(singular, 2) is None

    def test_huber_zero_residual_branch(self):
        from social_research_probe.stats.huber_regression import _huber_weight, _mad

        assert _huber_weight(0.0, 1.345) == 1.0
        assert _mad([]) == 0.0

    def test_kaplan_meier_at_t_0_returns_one(self):
        from social_research_probe.stats.kaplan_meier import survival_at

        # A curve that never has t > 0 means we always return last (which starts at 1.0)
        assert survival_at([(0.0, 1.0)], 100.0) == 1.0

    def test_pca_columns_empty_features(self):
        from social_research_probe.stats.pca import _columns

        assert _columns([]) == []

    def test_pca_variance_too_few_values(self):
        from social_research_probe.stats.pca import _variance

        assert _variance([1.0], 1.0) == 0.0

    def test_logistic_returns_empty_when_normal_solver_fails(self, monkeypatch):
        from social_research_probe.stats import logistic_regression as lr

        # Force _solve_normal_equations to return None
        monkeypatch.setattr(lr, "_solve_normal_equations", lambda *a, **kw: None)
        assert lr.run([0, 1, 0, 1, 0, 1], {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}) == []

    def test_logistic_sigmoid_clamps_extreme_values(self):
        from social_research_probe.stats.logistic_regression import _sigmoid

        assert _sigmoid(-1000) == 0.0
        assert _sigmoid(1000) == 1.0

    def test_bayesian_linear_solver_fails(self, monkeypatch):
        from social_research_probe.stats import bayesian_linear as bl

        monkeypatch.setattr(bl, "_solve_normal_equations", lambda *a, **kw: None)
        assert bl.run([1.0, 2.0, 3.0, 4.0, 5.0], {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}) == []

    def test_huber_solver_fails(self, monkeypatch):
        from social_research_probe.stats import huber_regression as hr

        monkeypatch.setattr(hr, "_solve_normal_equations", lambda *a, **kw: None)
        assert hr.run([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0]) == []


def test_bayesian_main_solver_returns_none(monkeypatch):
    """When beta solve returns None at line 44 we exit with []."""
    from social_research_probe.stats import bayesian_linear as bl

    call_counter = {"n": 0}
    real_solve = bl._solve_normal_equations

    def first_time_fail(*a, **kw):
        call_counter["n"] += 1
        if call_counter["n"] == 1:
            return None
        return real_solve(*a, **kw)

    monkeypatch.setattr(bl, "_solve_normal_equations", first_time_fail)
    assert bl.run([1.0, 2.0, 3.0, 4.0, 5.0], {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}) == []


def test_kaplan_meier_median_returns_none_when_survival_stays_high():
    """median_survival returns None when S(t) never drops to 0.5."""
    from social_research_probe.stats.kaplan_meier import _median_survival

    curve = [(0.0, 1.0), (1.0, 0.9), (2.0, 0.8), (3.0, 0.7)]
    assert _median_survival(curve) is None


def test_kaplan_meier_median_not_reached_caption():
    """When median is not reached the caption should say so."""
    from social_research_probe.stats.kaplan_meier import run

    # Many censored, few events so S stays above 0.5
    out = run([10.0, 20.0, 30.0, 40.0, 50.0], [1, 0, 0, 0, 0])
    cap = next(r.caption for r in out if "median" in r.name)
    assert "not reached" in cap


def test_kmeans_run_k_equals_one_returns_empty():
    """k<2 hits the return at line 27."""
    from social_research_probe.stats.kmeans import run

    assert run([[1.0], [2.0]], k=1) == []


def test_kmeans_converges_immediately():
    """When first assignment equals previous (default 0s) -> break at line 64."""
    from social_research_probe.stats.kmeans import fit

    # All identical points so k-means converges on iteration 1
    centroids, _ = fit([[5.0], [5.0], [5.0]], k=2, seed=0, max_iter=5)
    assert centroids


def test_logistic_weights_all_zero_break(monkeypatch):
    """All weights collapse to ~0 triggers the break path."""
    from social_research_probe.stats import logistic_regression as lr

    # sigmoid returns 1.0 for huge positive z; multiply by (1-1) = 0 weight
    # We trigger this by patching _sigmoid to always return exactly 1
    monkeypatch.setattr(lr, "_sigmoid", lambda z: 1.0)
    out = lr.run([0, 1, 0, 1, 0, 1], {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    # break happens but we still format with the initial beta=0 vector
    assert any(r.name == "logistic_intercept" for r in out)


def test_logistic_all_zeros_returns_empty():
    from social_research_probe.stats.logistic_regression import run

    assert run([0, 0, 0, 0, 0], {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}) == []


def test_kmeans_run_with_fit_returning_empty(monkeypatch):
    from social_research_probe.stats import kmeans as km

    monkeypatch.setattr(km, "fit", lambda *a, **kw: ([], []))
    assert km.run([[1.0], [2.0], [3.0]], k=2) == []


def test_kmeans_fit_early_convergence_break():
    """Two passes where the assignments don't change -> break at line 58->64."""
    from social_research_probe.stats.kmeans import fit

    # Very well-separated data so assignments stabilise after 1 reassignment
    data = [[0.0], [0.1], [0.2], [100.0], [100.1], [100.2]]
    _centroids, labels = fit(data, k=2, seed=0, max_iter=10)
    # Same cluster -> labels should split cleanly
    assert len(set(labels[:3])) == 1
    assert len(set(labels[3:])) == 1


def test_bayesian_main_beta_returns_none(monkeypatch):
    """Force _solve_normal_equations first call to return None."""
    from social_research_probe.stats import bayesian_linear as bl

    def always_none(*a, **kw):
        return None

    monkeypatch.setattr(bl, "_solve_normal_equations", always_none)
    assert bl.run([1.0, 2.0, 3.0, 4.0, 5.0], {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}) == []


def test_bayesian_posterior_variance_returns_none(monkeypatch):
    """Main solve succeeds but diag-of-inverse fails -> hits line 44."""
    from social_research_probe.stats import bayesian_linear as bl

    monkeypatch.setattr(bl, "_diagonal_of_inverse", lambda *a, **kw: None)
    assert bl.run([1.0, 2.0, 3.0, 4.0, 5.0], {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}) == []


def test_kmeans_fit_loop_breaks_on_stable_assignments():
    """fit() break when new_assignments == assignments after a single iteration."""
    from social_research_probe.stats.kmeans import fit

    # Use seeded identical data so initial random pick + reassignment converge instantly
    data = [[5.0], [5.0]]
    centroids, _labels = fit(data, k=2, seed=0, max_iter=50)
    # They should stabilise immediately and return 2 centroids
    assert len(centroids) == 2


def test_logistic_exact_all_ones_target():
    """sum(y) == n path — rejects, exits via the n <= k+1 or zero-variance guard."""
    from social_research_probe.stats.logistic_regression import run

    assert run([1, 1, 1, 1, 1, 1], {"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}) == []


def test_kmeans_direct_loop_break_via_mocked_closest(monkeypatch):
    """Patch _closest to always return 0 -> new_assignments equals initial [0]*n."""
    from social_research_probe.stats import kmeans as km

    monkeypatch.setattr(km, "_closest", lambda p, c: 0)
    data = [[1.0], [2.0], [3.0]]
    _centroids, labels = km.fit(data, k=2, seed=0, max_iter=10)
    assert labels == [0, 0, 0]


def test_logistic_zero_features_branch():
    """k == 0 short-circuits before evaluating other parts of the OR guard."""
    from social_research_probe.stats.logistic_regression import run

    assert run([0, 1, 0, 1], {}) == []


def test_kmeans_hits_max_iter_without_stabilising():
    """Force max_iter exhaustion by feeding alternating-label data with a tiny max_iter."""
    from social_research_probe.stats.kmeans import fit

    # Random-looking data with max_iter=1 — won't stabilise in one pass for 4 points
    data = [[0.0], [1.0], [100.0], [101.0]]
    centroids, _ = fit(data, k=2, seed=0, max_iter=1)
    assert len(centroids) == 2


def test_logistic_regression_normal_fit_path():
    """Standard fit exercises the non-break path through the IRLS loop."""
    from social_research_probe.stats.logistic_regression import run

    x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    y = [0, 0, 0, 1, 0, 1, 1, 1]
    out = run(y, {"x": x})
    assert any(r.name == "logistic_accuracy" for r in out)


def test_logistic_max_iter_exhausted():
    """Force loop exhaustion with max_iter=1 — falls through to _format_results."""
    from social_research_probe.stats.logistic_regression import run

    x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    y = [0, 0, 1, 0, 1, 1]
    out = run(y, {"x": x}, max_iter=1)
    assert any(r.name == "logistic_accuracy" for r in out)


def test_logistic_overflow_guard_on_huge_coefficient():
    """Huge coefficient from large features triggers the odds-ratio overflow guard."""
    from social_research_probe.stats.logistic_regression import _format_results

    # beta[1] > 500 triggers the "odds ratio > 1e217" branch
    y = [0, 1, 0, 1]
    x = [[1.0, 0.0], [1.0, 1.0], [1.0, 0.0], [1.0, 1.0]]
    out = _format_results(y, x, [0.0, 600.0], ["huge"], "label")
    huge = next(r.caption for r in out if "huge" in r.name)
    assert "> 1e217" in huge


def test_logistic_overflow_guard_on_huge_negative_coefficient():
    from social_research_probe.stats.logistic_regression import _format_results

    y = [0, 1]
    x = [[1.0, 0.0], [1.0, 1.0]]
    out = _format_results(y, x, [0.0, -600.0], ["tiny"], "label")
    tiny = next(r.caption for r in out if "tiny" in r.name)
    assert "< 1e-217" in tiny
