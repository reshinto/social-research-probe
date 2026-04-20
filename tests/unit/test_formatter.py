"""Tests for social_research_probe/synthesize/formatter.py."""

from __future__ import annotations

from social_research_probe.synthesize.explanations import (
    contextual_explanation as _contextual_explanation,
)
from social_research_probe.synthesize.explanations import (
    explain_bayesian as _explain_bayesian,
)
from social_research_probe.synthesize.explanations import (
    explain_bootstrap as _explain_bootstrap,
)
from social_research_probe.synthesize.explanations import (
    explain_correlation as _explain_correlation,
)
from social_research_probe.synthesize.explanations import (
    explain_descriptive as _explain_descriptive,
)
from social_research_probe.synthesize.explanations import (
    explain_huber as _explain_huber,
)
from social_research_probe.synthesize.explanations import (
    explain_kaplan_meier as _explain_kaplan_meier,
)
from social_research_probe.synthesize.explanations import (
    explain_kmeans as _explain_kmeans,
)
from social_research_probe.synthesize.explanations import (
    explain_multi_regression as _explain_multi_regression,
)
from social_research_probe.synthesize.explanations import (
    explain_naive_bayes as _explain_naive_bayes,
)
from social_research_probe.synthesize.explanations import (
    explain_outliers as _explain_outliers,
)
from social_research_probe.synthesize.explanations import (
    explain_pca as _explain_pca,
)
from social_research_probe.synthesize.explanations import (
    explain_polynomial as _explain_polynomial,
)
from social_research_probe.synthesize.explanations import (
    explain_regression as _explain_regression,
)
from social_research_probe.synthesize.explanations import (
    explain_spearman as _explain_spearman,
)
from social_research_probe.synthesize.explanations import (
    explain_spread as _explain_spread,
)
from social_research_probe.synthesize.explanations import (
    explain_tests as _explain_tests,
)
from social_research_probe.synthesize.explanations import (
    infer_model as _infer_model,
)
from social_research_probe.synthesize.explanations._common import parse_numeric as _val
from social_research_probe.synthesize.formatter import (
    _highlights_table,
    _items_table,
    build_packet,
    render_full,
    render_sections_1_9,
)
from social_research_probe.synthesize.formatter import (
    _to_bullets as _bulletise,
)

_ITEM = {
    "title": "A",
    "channel": "C",
    "url": "u",
    "source_class": "primary",
    "scores": {"trust": 0.9, "trend": 0.5, "opportunity": 0.4, "overall": 0.7},
    "one_line_takeaway": "x",
}

_SVS = {
    "validated": 1,
    "partially": 0,
    "unverified": 0,
    "low_trust": 0,
    "primary": 1,
    "secondary": 0,
    "commentary": 0,
    "notes": "",
}

_EMPTY_SVS = {k: 0 for k in _SVS}
_EMPTY_SVS["notes"] = ""


def _make_packet(**overrides):
    base = dict(
        topic="ai agents",
        platform="youtube",
        purpose_set=["trends"],
        items_top5=[_ITEM],
        source_validation_summary=_SVS,
        platform_signals_summary="ok",
        evidence_summary="ok",
        stats_summary={"models_run": ["descriptive"], "highlights": [], "low_confidence": False},
        chart_captions=[],
        warnings=[],
    )
    base.update(overrides)
    return base


def test_build_packet_shape():
    pkt = build_packet(**_make_packet())
    assert pkt["topic"] == "ai agents"
    assert "compiled_synthesis" not in pkt
    assert "opportunity_analysis" not in pkt


def test_render_sections_contains_headings():
    out = render_sections_1_9(
        {
            "topic": "ai",
            "platform": "youtube",
            "purpose_set": ["trends"],
            "items_top5": [],
            "source_validation_summary": _EMPTY_SVS,
            "platform_signals_summary": "-",
            "evidence_summary": "-",
            "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
            "chart_captions": [],
            "warnings": [],
        }
    )
    for h in ("## 1.", "## 2.", "## 9."):
        assert h in out


def test_render_sections_with_items():
    table = _items_table([_ITEM])
    assert "| Channel |" in table
    assert "0.90" in table
    assert "A" in table
    assert _bulletise("a; b; c") == "- a\n- b\n- c"

    table_with_pipe = _items_table([{**_ITEM, "title": "Pipe | Title"}])
    assert r"Pipe \| Title" in table_with_pipe

    out = render_sections_1_9(
        {
            "topic": "ai",
            "platform": "youtube",
            "purpose_set": ["trends"],
            "items_top5": [_ITEM],
            "source_validation_summary": {**_SVS, "unverified": 1},
            "platform_signals_summary": "5 items fetched",
            "evidence_summary": "live fetch",
            "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
            "chart_captions": [],
            "warnings": [],
        }
    )
    assert "## 3. Top Items" in out
    assert "A" in out


# ---------------------------------------------------------------------------
# _infer_model
# ---------------------------------------------------------------------------


def test_infer_model_known():
    assert _infer_model("Mean overall: 0.72") == "descriptive"
    assert _infer_model("Std dev: 0.04") == "spread"
    assert _infer_model("Huber slope: -0.005") == "huber_regression"
    assert _infer_model("Bayesian coef trust: 0.4 [0.3, 0.5]") == "bayesian_linear"


def test_infer_model_unknown_returns_empty():
    assert _infer_model("Totally unknown metric") == ""


# ---------------------------------------------------------------------------
# _val
# ---------------------------------------------------------------------------


def test_val_with_numeric():
    assert _val("Mean overall: 0.72") == 0.72


def test_val_negative():
    assert _val("Huber slope: -0.003") == -0.003


def test_val_no_match_returns_none():
    assert _val("no colon here") is None


# ---------------------------------------------------------------------------
# _explain_descriptive
# ---------------------------------------------------------------------------


def test_explain_descriptive_mean_high():
    r = _explain_descriptive("Mean overall: 0.80")
    assert "High baseline" in r


def test_explain_descriptive_mean_moderate():
    r = _explain_descriptive("Mean overall: 0.68")
    assert "Moderate baseline" in r


def test_explain_descriptive_mean_low():
    r = _explain_descriptive("Mean overall: 0.50")
    assert "Low baseline" in r


def test_explain_descriptive_median():
    r = _explain_descriptive("Median overall: 0.65")
    assert "Median" in r and "0.65" in r


def test_explain_descriptive_min():
    r = _explain_descriptive("Min overall: 0.30")
    assert "Floor" in r


def test_explain_descriptive_max():
    r = _explain_descriptive("Max overall: 0.95")
    assert "Ceiling" in r


def test_explain_descriptive_no_value():
    assert _explain_descriptive("Mean overall: none") == ""


# ---------------------------------------------------------------------------
# _explain_spread
# ---------------------------------------------------------------------------


def test_explain_spread_std_very_tight():
    r = _explain_spread("Std dev overall: 0.02")
    assert "Very tight" in r


def test_explain_spread_std_tight():
    r = _explain_spread("Std dev overall: 0.05")
    assert "Tight" in r


def test_explain_spread_std_wide():
    r = _explain_spread("Std dev overall: 0.10")
    assert "Wide" in r


def test_explain_spread_iqr_small():
    r = _explain_spread("Interquartile range: 0.03")
    assert "Middle 50%" in r and "very little" in r


def test_explain_spread_iqr_large():
    r = _explain_spread("Interquartile range: 0.12")
    assert "Middle 50%" in r and "matters" in r


def test_explain_spread_range_wide():
    r = _explain_spread("Range of overall: 0.30")
    assert "Wide range" in r


def test_explain_spread_range_narrow():
    r = _explain_spread("Range of overall: 0.10")
    assert "Narrow range" in r


def test_explain_spread_skewness_left():
    r = _explain_spread("Skewness: -0.5")
    assert "Left-skewed" in r


def test_explain_spread_skewness_right():
    r = _explain_spread("Skewness: 0.5")
    assert "Right-skewed" in r


def test_explain_spread_skewness_symmetric():
    r = _explain_spread("Skewness: 0.1")
    assert "Near-symmetric" in r


def test_explain_spread_kurtosis_fat():
    r = _explain_spread("Excess kurtosis: 1.5")
    assert "Fat tails" in r


def test_explain_spread_kurtosis_thin():
    r = _explain_spread("Excess kurtosis: -1.5")
    assert "Thin tails" in r


def test_explain_spread_kurtosis_normal():
    r = _explain_spread("Excess kurtosis: 0.5")
    assert "Normal tails" in r


def test_explain_spread_no_value():
    assert _explain_spread("Std dev overall: none") == ""


def test_explain_spread_unknown_prefix():
    assert _explain_spread("Unknown spread metric: 0.1") == ""


# ---------------------------------------------------------------------------
# _explain_regression
# ---------------------------------------------------------------------------


def test_explain_regression_slope_steep():
    r = _explain_regression("Linear trend slope: -0.010")
    assert "Steep" in r


def test_explain_regression_slope_gradual():
    r = _explain_regression("Linear trend slope: -0.005")
    assert "Gradual" in r


def test_explain_regression_slope_flat():
    r = _explain_regression("Linear trend slope: -0.001")
    assert "Flat" in r


def test_explain_regression_rsquared_strong():
    r = _explain_regression("R-squared (goodness of fit): 0.90")
    assert "Strong fit" in r


def test_explain_regression_rsquared_moderate():
    r = _explain_regression("R-squared (goodness of fit): 0.70")
    assert "Moderate fit" in r


def test_explain_regression_rsquared_weak():
    r = _explain_regression("R-squared (goodness of fit): 0.40")
    assert "Weak fit" in r


def test_explain_regression_growth_locking_in():
    r = _explain_regression("Average period-over-period growth: -1.0")
    assert "locking in" in r


def test_explain_regression_growth_flux():
    r = _explain_regression("Average period-over-period growth: 1.0")
    assert "still in flux" in r


def test_explain_regression_growth_stable():
    r = _explain_regression("Average period-over-period growth: 0.0")
    assert "stable" in r


def test_explain_regression_no_value():
    assert _explain_regression("Linear trend slope: none") == ""


# ---------------------------------------------------------------------------
# _explain_outliers
# ---------------------------------------------------------------------------


def test_explain_outliers_zero():
    r = _explain_outliers("Outliers in overall: 0 of 8")
    assert "No outliers" in r


def test_explain_outliers_few():
    r = _explain_outliers("Outliers in overall: 1 of 8")
    assert "outlier(s)" in r


def test_explain_outliers_many():
    r = _explain_outliers("Outliers in overall: 4 of 8")
    assert "significant noise" in r.lower() or "outliers" in r


def test_explain_outliers_no_match():
    assert _explain_outliers("Outliers in overall: bad format") == ""


def test_explain_outliers_fraction_zero():
    r = _explain_outliers("Outlier fraction overall: 0")
    assert "clean" in r


def test_explain_outliers_fraction_small():
    r = _explain_outliers("Outlier fraction overall: 5")
    assert "%" in r or "trustworthy" in r


def test_explain_outliers_fraction_large():
    r = _explain_outliers("Outlier fraction overall: 50")
    assert "caution" in r.lower() or "%" in r


def test_explain_outliers_fraction_no_value():
    assert _explain_outliers("Outlier fraction overall: none") == ""


def test_explain_outliers_unknown_prefix():
    assert _explain_outliers("Unknown outlier metric") == ""


# ---------------------------------------------------------------------------
# _explain_correlation
# ---------------------------------------------------------------------------


def test_explain_correlation_strong_negative():
    r = _explain_correlation("Pearson r between trust and trend: -0.70")
    assert "Strong tradeoff" in r


def test_explain_correlation_weak_negative():
    r = _explain_correlation("Pearson r between trust and trend: -0.30")
    assert "Weak tradeoff" in r


def test_explain_correlation_strong_positive():
    r = _explain_correlation("Pearson r between trust and trend: 0.70")
    assert "Strong alignment" in r


def test_explain_correlation_weak_positive():
    r = _explain_correlation("Pearson r between trust and trend: 0.30")
    assert "Weak alignment" in r


def test_explain_correlation_neutral():
    r = _explain_correlation("Pearson r between trust and trend: 0.10")
    assert "No meaningful relationship" in r


def test_explain_correlation_no_value():
    assert _explain_correlation("Pearson r between trust and trend: none") == ""


# ---------------------------------------------------------------------------
# _explain_spearman
# ---------------------------------------------------------------------------


def test_explain_spearman_strong():
    r = _explain_spearman("Spearman between trust and trend: 0.70")
    assert "structural" in r or "confirms" in r


def test_explain_spearman_weak():
    r = _explain_spearman("Spearman between trust and trend: 0.20")
    assert "Weak" in r or "weak" in r


def test_explain_spearman_no_value():
    assert _explain_spearman("Spearman between trust and trend: none") == ""


# ---------------------------------------------------------------------------
# _explain_tests
# ---------------------------------------------------------------------------


def test_explain_tests_mann_whitney():
    r = _explain_tests("Mann-Whitney U test", "p=0.02")
    assert "statistically distinct" in r


def test_explain_tests_welch_with_diff():
    r = _explain_tests("Welch t-test diff=0.150", "p=0.01")
    assert "0.150" in r


def test_explain_tests_welch_no_diff():
    r = _explain_tests("Welch t-test: p=0.03", "")
    assert "different" in r


def test_explain_tests_normality_non_normal():
    r = _explain_tests("Normality check", "non-normal distribution")
    assert "Non-normal" in r or "median" in r


def test_explain_tests_normality_normal():
    r = _explain_tests("Normality check: normal", "")
    assert "Bell-curve" in r or "reliable" in r


def test_explain_tests_unknown():
    assert _explain_tests("Unknown test metric", "") == ""


# ---------------------------------------------------------------------------
# _explain_polynomial
# ---------------------------------------------------------------------------


def test_explain_polynomial_deg2_rsq_high():
    r = _explain_polynomial("Polynomial (degree 2) R²: 0.90")
    assert "Curved fit" in r and "accelerates" in r


def test_explain_polynomial_deg2_rsq_low():
    r = _explain_polynomial("Polynomial (degree 2) R²: 0.60")
    assert "Curved fit" in r and "linear" in r


def test_explain_polynomial_deg2_leading_steep():
    r = _explain_polynomial("Polynomial (degree 2) leading: -0.0005")
    assert "Steep curve" in r


def test_explain_polynomial_deg2_leading_shallow():
    r = _explain_polynomial("Polynomial (degree 2) leading: -0.0001")
    assert "Shallow curve" in r


def test_explain_polynomial_deg3_rsq():
    r = _explain_polynomial("Polynomial (degree 3) R²: 0.88")
    assert "Best-fit" in r


def test_explain_polynomial_deg3_leading():
    r = _explain_polynomial("Polynomial (degree 3) leading: 0.00001")
    assert "S-curve" in r


def test_explain_polynomial_no_value():
    assert _explain_polynomial("Polynomial (degree 2) R²: none") == ""


# ---------------------------------------------------------------------------
# _explain_bootstrap
# ---------------------------------------------------------------------------


def test_explain_bootstrap_ci_lower():
    r = _explain_bootstrap("Bootstrap CI lower: 0.600", "")
    assert "0.600" in r


def test_explain_bootstrap_ci_upper():
    r = _explain_bootstrap("Bootstrap CI upper: 0.850", "")
    assert "0.850" in r


def test_explain_bootstrap_mean_with_ci():
    r = _explain_bootstrap("Bootstrap mean: 0.720", "finding [0.680, 0.760]")
    assert "0.720" in r and "0.680" in r


def test_explain_bootstrap_mean_without_ci():
    r = _explain_bootstrap("Bootstrap mean: 0.720", "no bracket here")
    assert "stable" in r.lower()


def test_explain_bootstrap_ci_lower_no_value():
    assert _explain_bootstrap("Bootstrap CI lower: none", "") == ""


def test_explain_bootstrap_ci_upper_no_value():
    assert _explain_bootstrap("Bootstrap CI upper: none", "") == ""


def test_explain_bootstrap_unknown():
    assert _explain_bootstrap("Bootstrap unknown metric", "") == ""


# ---------------------------------------------------------------------------
# _explain_multi_regression
# ---------------------------------------------------------------------------


def test_explain_multi_regression_intercept():
    r = _explain_multi_regression("Intercept for overall: 0.05")
    assert "Formula offset" in r or "offset" in r


def test_explain_multi_regression_trust():
    r = _explain_multi_regression("Coefficient for trust: 0.50")
    assert "Trust" in r and "50%" in r


def test_explain_multi_regression_trust_no_value():
    assert _explain_multi_regression("Coefficient for trust: none") == ""


def test_explain_multi_regression_trend():
    r = _explain_multi_regression("Coefficient for trend: 0.33")
    assert "Trend" in r


def test_explain_multi_regression_trend_no_value():
    assert _explain_multi_regression("Coefficient for trend: none") == ""


def test_explain_multi_regression_opportunity():
    r = _explain_multi_regression("Coefficient for opportunity: 0.17")
    assert "Opportunity" in r


def test_explain_multi_regression_opportunity_no_value():
    assert _explain_multi_regression("Coefficient for opportunity: none") == ""


def test_explain_multi_regression_rsq_perfect():
    r = _explain_multi_regression("Multi-regression R²: 1.000")
    assert "Perfect fit" in r or "deterministic" in r


def test_explain_multi_regression_rsq_high():
    r = _explain_multi_regression("Multi-regression R²: 0.95")
    assert "95%" in r or "explains" in r


def test_explain_multi_regression_adjusted_rsq():
    r = _explain_multi_regression("Adjusted R²: 0.92")
    assert "92%" in r or "explains" in r


def test_explain_multi_regression_unknown():
    assert _explain_multi_regression("Coefficient for unknown_factor: 0.20") == ""


# ---------------------------------------------------------------------------
# _explain_kmeans
# ---------------------------------------------------------------------------


def test_explain_kmeans_within():
    r = _explain_kmeans("K-means (k=3) within-cluster sum: 0.05")
    assert "Three market tiers" in r


def test_explain_kmeans_cluster_singleton():
    r = _explain_kmeans("K-means cluster 0 contains 1/8")
    assert "Singleton" in r or "one video" in r


def test_explain_kmeans_cluster_dominant():
    r = _explain_kmeans("K-means cluster 0 contains 5/8")
    assert "Dominant" in r or "mainstream" in r


def test_explain_kmeans_cluster_minority():
    r = _explain_kmeans("K-means cluster 1 contains 3/8")
    assert "3/8" in r or "smaller" in r


def test_explain_kmeans_cluster_no_match():
    assert _explain_kmeans("K-means cluster 0 bad format") == ""


def test_explain_kmeans_unknown():
    assert _explain_kmeans("K-means unknown metric") == ""


# ---------------------------------------------------------------------------
# _explain_pca
# ---------------------------------------------------------------------------


def test_explain_pca_pc1():
    r = _explain_pca("PC1 variance explained: 0.85", "top loadings: subscriber=0.95")
    assert "Subscriber" in r or "subscriber" in r or "differentiator" in r


def test_explain_pca_pc2():
    r = _explain_pca("PC2 variance: 0.10", "")
    assert "second" in r.lower() or "secondary" in r.lower()


def test_explain_pca_unknown():
    assert _explain_pca("PCX variance: 0.10", "") == ""


# ---------------------------------------------------------------------------
# _explain_kaplan_meier
# ---------------------------------------------------------------------------


def test_explain_kaplan_meier_median_not_reached():
    r = _explain_kaplan_meier("Kaplan-Meier median survival: not reached", "")
    assert "durable" in r or "long-term" in r


def test_explain_kaplan_meier_median_days():
    r = _explain_kaplan_meier("Kaplan-Meier median survival: 14.0 days", "")
    assert "14" in r


def test_explain_kaplan_meier_median_no_days():
    r = _explain_kaplan_meier("Kaplan-Meier median survival: none", "")
    assert r == ""


def test_explain_kaplan_meier_s30_high():
    r = _explain_kaplan_meier("Kaplan-Meier S(t=30d): 0.75", "")
    assert "75%" in r or "%" in r


def test_explain_kaplan_meier_s30_medium():
    r = _explain_kaplan_meier("Kaplan-Meier S(t=30d): 0.45", "")
    assert "moderate" in r.lower() or "%" in r


def test_explain_kaplan_meier_s30_low():
    r = _explain_kaplan_meier("Kaplan-Meier S(t=30d): 0.20", "")
    assert "fast-burn" in r or "%" in r


def test_explain_kaplan_meier_s30_no_value():
    assert _explain_kaplan_meier("Kaplan-Meier S(t=30d): none", "") == ""


def test_explain_kaplan_meier_unknown():
    assert _explain_kaplan_meier("Kaplan-Meier unknown metric", "") == ""


# ---------------------------------------------------------------------------
# _explain_naive_bayes
# ---------------------------------------------------------------------------


def test_explain_naive_bayes_prior_not_top5():
    r = _explain_naive_bayes("Naive Bayes prior P(is_top_5=0): 0.80")
    assert "80%" in r or "Base odds" in r


def test_explain_naive_bayes_prior_not_top5_no_value():
    assert _explain_naive_bayes("Naive Bayes prior P(is_top_5=0): none") == ""


def test_explain_naive_bayes_prior_top5():
    r = _explain_naive_bayes("Naive Bayes prior P(is_top_5=1): 0.20")
    assert "top 5" in r or "1 in" in r


def test_explain_naive_bayes_prior_top5_no_value():
    assert _explain_naive_bayes("Naive Bayes prior P(is_top_5=1): none") == ""


def test_explain_naive_bayes_accuracy_high():
    r = _explain_naive_bayes("Naive Bayes training accuracy: 0.95")
    assert "95%" in r or "reliable" in r


def test_explain_naive_bayes_accuracy_medium():
    r = _explain_naive_bayes("Naive Bayes training accuracy: 0.80")
    assert "80%" in r or "useful" in r


def test_explain_naive_bayes_accuracy_low():
    r = _explain_naive_bayes("Naive Bayes training accuracy: 0.60")
    assert "Low accuracy" in r or "weak" in r


def test_explain_naive_bayes_accuracy_no_value():
    assert _explain_naive_bayes("Naive Bayes training accuracy: none") == ""


def test_explain_naive_bayes_unknown():
    assert _explain_naive_bayes("Naive Bayes unknown metric: 0.5") == ""


# ---------------------------------------------------------------------------
# _explain_huber
# ---------------------------------------------------------------------------


def test_explain_huber_intercept():
    r = _explain_huber("Huber intercept: 0.720")
    assert "0.720" in r


def test_explain_huber_slope():
    r = _explain_huber("Huber slope: -0.0040")
    assert "0.0040" in r


def test_explain_huber_rsq():
    r = _explain_huber("Huber R²: 0.85")
    assert "85%" in r or "%" in r


def test_explain_huber_no_value():
    assert _explain_huber("Huber intercept: none") == ""


def test_explain_huber_unknown():
    assert _explain_huber("Huber unknown: none") == ""


# ---------------------------------------------------------------------------
# _explain_bayesian
# ---------------------------------------------------------------------------


def test_explain_bayesian_intercept_with_sd():
    r = _explain_bayesian("Bayesian intercept: 0.050 SD 0.003", "")
    assert "0.050" in r and "0.003" in r


def test_explain_bayesian_intercept_no_sd():
    r = _explain_bayesian("Bayesian intercept: 0.050", "")
    assert r == ""


def test_explain_bayesian_residual_low():
    r = _explain_bayesian("Bayesian residual variance: 0.0005", "")
    assert "zero" in r.lower() or "unexplained" in r


def test_explain_bayesian_residual_higher():
    r = _explain_bayesian("Bayesian residual variance: 0.005", "")
    assert "non-zero" in r or "small" in r or "residual" in r


def test_explain_bayesian_residual_no_value():
    assert _explain_bayesian("Bayesian residual variance: none", "") == ""


def test_explain_bayesian_coef_trust():
    r = _explain_bayesian("Bayesian coef trust: 0.40 [0.35, 0.45]", "finding [0.35, 0.45]")
    assert "Trust" in r and "0.40" in r


def test_explain_bayesian_coef_trend():
    r = _explain_bayesian("Bayesian coef trend: 0.30 [0.25, 0.35]", "finding [0.25, 0.35]")
    assert "Trend" in r and "0.30" in r


def test_explain_bayesian_coef_opportunity():
    r = _explain_bayesian("Bayesian coef opportunity: 0.20 [0.15, 0.25]", "finding [0.15, 0.25]")
    assert "Opportunity" in r and "0.20" in r


def test_explain_bayesian_coef_no_match():
    assert _explain_bayesian("Bayesian coef unknown: 0.50 no brackets", "") == ""


# ---------------------------------------------------------------------------
# _contextual_explanation dispatch
# ---------------------------------------------------------------------------


def test_contextual_explanation_descriptive():
    r = _contextual_explanation("Mean overall: 0.80", "")
    assert r  # non-empty


def test_contextual_explanation_spread():
    r = _contextual_explanation("Std dev: 0.05", "")
    assert r


def test_contextual_explanation_regression():
    r = _contextual_explanation("Linear trend slope: -0.005", "")
    assert r


def test_contextual_explanation_growth():
    r = _contextual_explanation("Average period-over-period growth: -1.0", "")
    assert r


def test_contextual_explanation_outliers():
    r = _contextual_explanation("Outliers in overall: 0 of 8", "")
    assert r


def test_contextual_explanation_correlation():
    r = _contextual_explanation("Pearson r between trust and trend: 0.70", "")
    assert r


def test_contextual_explanation_spearman():
    r = _contextual_explanation("Spearman between trust and trend: 0.60", "")
    assert r


def test_contextual_explanation_mann_whitney():
    r = _contextual_explanation("Mann-Whitney U test", "p=0.02")
    assert r


def test_contextual_explanation_welch():
    r = _contextual_explanation("Welch t-test diff=0.10", "p=0.01")
    assert r


def test_contextual_explanation_normality():
    r = _contextual_explanation("Normality check: normal", "")
    assert r


def test_contextual_explanation_polynomial_deg2():
    r = _contextual_explanation("Polynomial (degree 2) R²: 0.80", "")
    assert r


def test_contextual_explanation_polynomial_deg3():
    r = _contextual_explanation("Polynomial (degree 3) R²: 0.80", "")
    assert r


def test_contextual_explanation_bootstrap():
    r = _contextual_explanation("Bootstrap CI lower: 0.60", "")
    assert r


def test_contextual_explanation_multi_regression():
    r = _contextual_explanation("Multi-regression R²: 0.99", "")
    assert r


def test_contextual_explanation_kmeans():
    r = _contextual_explanation("K-means (k=3) within-cluster sum: 0.05", "")
    assert r


def test_contextual_explanation_pca():
    r = _contextual_explanation("PC1 variance explained: 0.85", "top loadings: subscriber=0.95")
    assert r


def test_contextual_explanation_kaplan_meier():
    r = _contextual_explanation("Kaplan-Meier median survival: not reached", "")
    assert r


def test_contextual_explanation_naive_bayes():
    r = _contextual_explanation("Naive Bayes prior P(is_top_5=1): 0.20", "")
    assert r


def test_contextual_explanation_huber():
    r = _contextual_explanation("Huber slope: -0.004", "")
    assert r


def test_contextual_explanation_bayesian():
    r = _contextual_explanation("Bayesian intercept: 0.050 SD 0.003", "")
    assert r


def test_contextual_explanation_unknown_model_returns_empty():
    assert _contextual_explanation("Unknown XYZ metric: 0.5", "") == ""


# ---------------------------------------------------------------------------
# _highlights_table
# ---------------------------------------------------------------------------


def test_highlights_table_empty():
    result = _highlights_table([])
    assert result == "_(no highlights)_"


def test_highlights_table_single_entry():
    result = _highlights_table(["Mean overall: 0.72 — finding text"])
    assert "| Model |" in result
    assert "descriptive" in result
    assert "0.72" in result


def test_highlights_table_model_blank_for_repeated():
    highlights = [
        "Mean overall: 0.80 — f1",
        "Median overall: 0.75 — f2",
    ]
    result = _highlights_table(highlights)
    lines = result.strip().splitlines()
    # First data row has the model; second row has blank model cell
    assert "descriptive" in lines[2]
    assert lines[3].startswith("|  |") or "| |" in lines[3]


def test_highlights_table_escapes_pipe_in_metric():
    result = _highlights_table(["Mean pipe|name: 0.70 — result"])
    assert r"\|" in result


def test_highlights_table_entry_without_dash():
    result = _highlights_table(["Mean overall: 0.70"])
    assert "descriptive" in result
    assert "0.70" in result


# ---------------------------------------------------------------------------
# render_full
# ---------------------------------------------------------------------------


def test_render_full_without_synthesis():
    pkt = build_packet(**_make_packet())
    out = render_full(pkt)
    assert "## 10." in out
    assert "LLM synthesis unavailable" in out
    assert "## 11." in out


def test_render_full_with_synthesis():
    pkt = build_packet(**_make_packet())
    pkt["compiled_synthesis"] = "My synthesis."
    pkt["opportunity_analysis"] = "My opp."
    out = render_full(pkt)
    assert "My synthesis." in out
    assert "My opp." in out
    assert "LLM synthesis unavailable" not in out


def test_render_sections_1_9_low_confidence_flag():
    pkt = {
        "topic": "ai",
        "platform": "youtube",
        "purpose_set": ["trends"],
        "items_top5": [],
        "source_validation_summary": _EMPTY_SVS,
        "platform_signals_summary": "-",
        "evidence_summary": "-",
        "stats_summary": {"models_run": [], "highlights": [], "low_confidence": True},
        "chart_captions": ["Chart caption here"],
        "warnings": ["a warning"],
    }
    out = render_sections_1_9(pkt)
    assert "low confidence" in out
    assert "Chart caption here" in out
    assert "a warning" in out


def test_render_sections_1_9_notes_rendered():
    svs = {**_SVS, "notes": "some notes here"}
    pkt = {
        "topic": "ai",
        "platform": "youtube",
        "purpose_set": ["trends"],
        "items_top5": [],
        "source_validation_summary": svs,
        "platform_signals_summary": "-",
        "evidence_summary": "-",
        "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
        "chart_captions": [],
        "warnings": [],
    }
    out = render_sections_1_9(pkt)
    assert "some notes here" in out
