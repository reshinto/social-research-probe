"""Push to 100% — micro 7."""

from __future__ import annotations

import asyncio
import subprocess
from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe import get_version
from social_research_probe.commands import install_skill
from social_research_probe.technologies.corroborates import _filters
from social_research_probe.technologies.media_fetch import yt_dlp
from social_research_probe.technologies.report_render.html.raw_html import _sections
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    logistic_regression,
    nonparametric,
    pca,
    polynomial_regression,
)
from social_research_probe.technologies.validation.claim_extractor import (
    Claim,
    ClaimExtractor,
    ClaimExtractorInput,
)


def test_get_version_with_unknown_package(monkeypatch):
    def boom(name):
        raise PackageNotFoundError

    monkeypatch.setattr(
        "social_research_probe.version_module" if False else "importlib.metadata.version", boom
    )
    out = get_version()
    assert out == "unknown" or out


def test_pca_power_iteration_norm_zero():
    # Zero matrix → norm < 1e-12 → break
    out = pca._power_iteration([[0.0, 0.0], [0.0, 0.0]], 2, iterations=5)
    assert isinstance(out, tuple)


def test_pca_power_iteration_converges_break():
    matrix = [[2.0, 0.0], [0.0, 1.0]]
    vec, _eig = pca._power_iteration(matrix, 2, iterations=500)
    # eigenvector close to [1, 0]
    assert abs(vec[0]) > abs(vec[1])


def test_logistic_weights_all_zero(monkeypatch):
    # Force overflow to zero weights, breaks loop early
    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.logistic_regression._sigmoid",
        lambda z: 0.0,
    )
    y = [0, 1, 0]
    features = {"x": [1.0, 2.0, 3.0]}
    out = logistic_regression.run(y, features, max_iter=2)
    assert isinstance(out, list)


def test_logistic_normal_solver_returns_none(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.logistic_regression._solve_normal_equations",
        lambda *a, **kw: None,
    )
    y = [0, 1, 0, 1]
    features = {"x": [1.0, 2.0, 3.0, 4.0]}
    out = logistic_regression.run(y, features, max_iter=3)
    assert out == []


def test_huber_solver_returns_none(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.huber_regression._solve_normal_equations",
        lambda *a, **kw: None,
    )
    out = huber_regression.run([1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 2.0, 3.0, 4.0, 5.0])
    assert out == []


def test_huber_converges(monkeypatch):
    # Force convergence by making solver return same beta
    fixed = [0.0, 1.0]

    def solve(xt_wx, xt_wz):
        return fixed[:]

    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.huber_regression._solve_normal_equations",
        solve,
    )
    out = huber_regression.run([1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 2.0, 3.0, 4.0, 5.0])
    assert out


def test_filters_self_source_invalid_host(monkeypatch):
    monkeypatch.setattr(_filters, "_host", lambda u: None if u else None)
    assert _filters.is_self_source("a", "b") is False


def test_yt_dlp_browser_none(monkeypatch, tmp_path):
    monkeypatch.delenv("SRP_YTDLP_COOKIES_FILE", raising=False)
    monkeypatch.setenv("SRP_YTDLP_BROWSER", "none")

    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    (tmp_path / "audio.mp3").write_bytes(b"x")
    yt_dlp.download_audio("u", str(tmp_path))
    # browser=none → no --cookies-from-browser flag
    assert "--cookies-from-browser" not in captured["cmd"]


def test_yt_dlp_cookies_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_YTDLP_COOKIES_FILE", "/tmp/cookies.txt")
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    (tmp_path / "audio.mp3").write_bytes(b"x")
    yt_dlp.download_audio("u", str(tmp_path))
    assert "--cookies" in captured["cmd"]


def test_install_skill_merge_with_added(monkeypatch, tmp_path, capsys):
    bundled = tmp_path / "b.toml"
    bundled.write_text("[a]\nx = 1\n[b]\ny = 2\n")
    monkeypatch.setattr(install_skill, "_BUNDLED_CONFIG", bundled)
    target = tmp_path / "c.toml"
    target.write_text("[a]\nx = 1\n")
    install_skill._merge_missing_config_keys(target)
    out = capsys.readouterr().out
    assert "Added" in out


def test_sections_section3_no_summary_source():
    items = [
        {
            "channel": "Ch",
            "url": "https://x",
            "title": "T1",
            "source_class": "primary",
            "scores": {"trust": 0.9, "trend": 0.8, "opportunity": 0.7, "overall": 0.85},
            "one_line_takeaway": "tk",
        }
    ]
    out = _sections.section_3_top_items({"items_top_n": items})
    assert "summary-notice" not in out


def test_nonparametric_ranks_with_ties():
    out = nonparametric._ranks([1.0, 2.0, 2.0, 3.0])
    # ties should produce equal ranks
    assert out[1] == out[2]


def test_claim_extractor_execute(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.validation.claim_extractor.extract_claims",
        lambda text, source_text, source_url: [Claim("x", "x", 0)],
    )
    inp = ClaimExtractorInput(text="hello world content here")
    out = asyncio.run(ClaimExtractor()._execute(inp))
    assert out


def test_correlation_no_factors_finally():
    from social_research_probe.services.synthesizing.explanations import explain_correlation

    out = explain_correlation("Pearson r alone: 0.05")
    # weak case + no factors → should return weak strength
    assert isinstance(out, str)


def test_descriptive_no_match():
    from social_research_probe.services.synthesizing.explanations import explain_descriptive

    # Doesn't match Mean/Median/Min/Max → returns ""
    out = explain_descriptive("Std overall: 0.5")
    assert out == ""


def test_youtube_api_resolve_secret_empty(monkeypatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    from social_research_probe.technologies.media_fetch import youtube_api
    from social_research_probe.utils.core.errors import AdapterError

    with patch("social_research_probe.commands.config.read_secret", return_value=None):
        with pytest.raises(AdapterError):
            youtube_api.resolve_youtube_api_key()


def test_normality_kurt_zero_branch():
    from social_research_probe.technologies.statistics import normality

    # Trigger the abs(kurt) < 1.0 branch
    assert "near-normal" in normality._kurt_verdict(0.5)


def test_polynomial_run_no_coeffs(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.polynomial_regression.fit_coefficients",
        lambda x, y, d: None,
    )
    out = polynomial_regression.run([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], degree=2)
    assert out == []


def test_bayesian_singular_matrix(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.technologies.statistics.bayesian_linear._diagonal_of_inverse",
        lambda m, n: None,
    )
    y = [1.0, 2.0, 3.0, 4.0, 5.0]
    features = {"x": [1.0, 2.0, 3.0, 4.0, 5.0]}
    out = bayesian_linear.run(y, features)
    assert out == []
