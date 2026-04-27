"""Tests for charts: heatmap, regression_scatter, residuals, table."""

from __future__ import annotations

from pathlib import Path

from social_research_probe.technologies.charts import (
    heatmap,
    regression_scatter,
    residuals,
    table,
)


def test_heatmap_empty(tmp_path: Path):
    result = heatmap.render({}, output_dir=str(tmp_path))
    assert Path(result.path).exists()
    assert "0 features" in result.caption


def test_heatmap_basic(tmp_path: Path):
    feats = {"a": [1.0, 2.0, 3.0], "b": [3.0, 2.0, 1.0]}
    result = heatmap.render(feats, output_dir=str(tmp_path))
    assert Path(result.path).exists()


def test_heatmap_pearson_unequal():
    assert heatmap._pearson([1.0, 2.0], [1.0]) == 0.0


def test_heatmap_pearson_zero_denom():
    assert heatmap._pearson([1.0, 1.0, 1.0], [2.0, 2.0, 2.0]) == 0.0


def test_regression_scatter_short(tmp_path: Path):
    result = regression_scatter.render([1.0], [1.0], output_dir=str(tmp_path))
    assert Path(result.path).exists()


def test_regression_scatter_basic(tmp_path: Path):
    result = regression_scatter.render([1.0, 2.0, 3.0], [2.0, 4.0, 6.0], output_dir=str(tmp_path))
    assert Path(result.path).exists()
    assert "Regression" in result.caption


def test_residuals_too_few(tmp_path: Path):
    result = residuals.render([1.0], [1.0], output_dir=str(tmp_path))
    assert Path(result.path).exists()


def test_residuals_basic(tmp_path: Path):
    result = residuals.render([1.0, 2.0, 3.0, 4.0], [2.1, 3.9, 6.2, 8.1], output_dir=str(tmp_path))
    assert Path(result.path).exists()


def test_table_basic(tmp_path: Path):
    result = table.render([{"a": 1, "b": 2}, {"a": 3, "b": 4}], output_dir=str(tmp_path))
    assert Path(result.path).exists()
    assert "2 rows" in result.caption
