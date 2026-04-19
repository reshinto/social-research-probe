"""Tests for the advanced viz modules: regression scatter, histogram, heatmap, residuals."""

from __future__ import annotations

import os
import sys
import types
import unittest.mock as mock

from social_research_probe.viz import heatmap as heatmap_mod
from social_research_probe.viz import histogram as histogram_mod
from social_research_probe.viz import regression_scatter as regression_mod
from social_research_probe.viz import residuals as residuals_mod


def _install_fake_matplotlib(monkeypatch):
    fake_fig = mock.MagicMock()
    fake_plt = mock.MagicMock()
    fake_plt.figure.return_value = fake_fig
    fake_plt.subplots.return_value = (fake_fig, mock.MagicMock())
    fake_mpl = types.ModuleType("matplotlib")
    fake_mpl.use = mock.MagicMock()
    fake_mpl.pyplot = fake_plt
    monkeypatch.setitem(sys.modules, "matplotlib", fake_mpl)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_plt)
    return fake_plt


class TestRegressionScatter:
    def test_render_creates_png(self, tmp_path):
        result = regression_mod.render(
            [1.0, 2.0, 3.0], [2.0, 4.0, 6.0], label="rs", output_dir=str(tmp_path)
        )
        assert os.path.isfile(result.path)
        assert "Regression" in result.caption
        assert "R²" in result.caption

    def test_render_with_matplotlib_success(self, monkeypatch, tmp_path):
        fake_plt = _install_fake_matplotlib(monkeypatch)
        regression_mod._render_with_matplotlib(
            [1.0, 2.0, 3.0], [2.0, 4.0, 6.0], str(tmp_path / "x.png"), "lab", 2.0, 0.0, 1.0
        )
        fake_plt.savefig.assert_called_once()

    def test_render_with_matplotlib_empty_x_skips_line(self, monkeypatch, tmp_path):
        fake_plt = _install_fake_matplotlib(monkeypatch)
        regression_mod._render_with_matplotlib(
            [], [], str(tmp_path / "x.png"), "lab", 0.0, 0.0, 0.0
        )
        fake_plt.savefig.assert_called_once()

    def test_render_with_one_point_returns_zeros(self, tmp_path):
        result = regression_mod.render([1.0], [2.0], label="x", output_dir=str(tmp_path))
        assert "R²=0.000" in result.caption

    def test_fit_line_zero_variance(self):
        slope, intercept, r2 = regression_mod._fit_line([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])
        assert slope == 0.0
        assert intercept == 2.0
        assert r2 == 0.0


class TestHistogram:
    def test_render_creates_png(self, tmp_path):
        result = histogram_mod.render(
            [0.5, 0.6, 0.7, 0.8, 0.9], label="scores", output_dir=str(tmp_path)
        )
        assert os.path.isfile(result.path)
        assert "Histogram" in result.caption

    def test_render_empty_data_writes_placeholder(self, tmp_path):
        result = histogram_mod.render([], label="empty", output_dir=str(tmp_path))
        assert os.path.isfile(result.path)
        assert "0 items" in result.caption

    def test_render_with_matplotlib_success(self, monkeypatch, tmp_path):
        fake_plt = _install_fake_matplotlib(monkeypatch)
        histogram_mod._render_with_matplotlib([0.1, 0.2, 0.3], str(tmp_path / "h.png"), "x", 5)
        fake_plt.savefig.assert_called_once()


class TestHeatmap:
    def test_render_creates_png(self, tmp_path):
        features = {
            "a": [1.0, 2.0, 3.0],
            "b": [2.0, 4.0, 6.0],
            "c": [3.0, 1.0, 2.0],
        }
        result = heatmap_mod.render(features, output_dir=str(tmp_path))
        assert os.path.isfile(result.path)
        assert "3 features" in result.caption

    def test_render_empty_features_writes_placeholder(self, tmp_path):
        result = heatmap_mod.render({}, output_dir=str(tmp_path))
        assert os.path.isfile(result.path)
        assert "0 features" in result.caption

    def test_render_with_matplotlib_success(self, monkeypatch, tmp_path):
        fake_plt = _install_fake_matplotlib(monkeypatch)
        heatmap_mod._render_with_matplotlib(
            ["x", "y"], [[1.0, 0.5], [0.5, 1.0]], str(tmp_path / "hm.png"), "lab"
        )
        fake_plt.savefig.assert_called_once()

    def test_pearson_zero_variance(self):
        assert heatmap_mod._pearson([1.0, 1.0, 1.0], [2.0, 3.0, 4.0]) == 0.0

    def test_pearson_too_few_points(self):
        assert heatmap_mod._pearson([1.0], [2.0]) == 0.0


class TestResiduals:
    def test_render_creates_png(self, tmp_path):
        result = residuals_mod.render(
            [1.0, 2.0, 3.0, 4.0], [1.1, 2.2, 2.9, 4.1], label="r", output_dir=str(tmp_path)
        )
        assert os.path.isfile(result.path)
        assert "Residuals" in result.caption

    def test_render_too_few_points_writes_placeholder(self, tmp_path):
        result = residuals_mod.render([1.0], [2.0], label="r", output_dir=str(tmp_path))
        assert os.path.isfile(result.path)
        assert "0 points" in result.caption

    def test_render_with_matplotlib_success(self, monkeypatch, tmp_path):
        fake_plt = _install_fake_matplotlib(monkeypatch)
        residuals_mod._render_with_matplotlib([0.1, 0.2], [0.0, 0.05], str(tmp_path / "r.png"), "x")
        fake_plt.savefig.assert_called_once()

    def test_fit_zero_variance_returns_zero_slope(self):
        fitted, residuals = residuals_mod._fit_and_residuals([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])
        assert fitted == [2.0, 2.0, 2.0]
        assert residuals == [-1.0, 0.0, 1.0]
