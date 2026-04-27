"""Tests for tech.charts: ascii, bar, line, scatter, histogram, selector, png writer."""

from __future__ import annotations

from pathlib import Path

from social_research_probe.technologies.charts import (
    _png_writer,
    ascii,
    bar,
    histogram,
    line,
    scatter,
    selector,
)
from social_research_probe.technologies.charts.base import ChartResult


class TestAscii:
    def test_empty(self):
        out = ascii.render_bars([])
        assert "no data" in out

    def test_basic(self):
        out = ascii.render_bars([1.0, 2.0, 3.0], label="x")
        assert "x" in out
        assert "█" in out


class TestBarRender:
    def test_returns_chart_result(self, tmp_path: Path):
        result = bar.render([1.0, 2.0, 3.0], label="metric", output_dir=str(tmp_path))
        assert isinstance(result, ChartResult)
        assert Path(result.path).exists()
        assert "Bar chart" in result.caption


class TestLineRender:
    def test_returns_chart_result(self, tmp_path: Path):
        result = line.render([1.0, 2.0, 3.0, 4.0], label="trend", output_dir=str(tmp_path))
        assert isinstance(result, ChartResult)
        assert Path(result.path).exists()


class TestScatterRender:
    def test_returns_chart_result(self, tmp_path: Path):
        result = scatter.render([1.0, 2.0], [3.0, 4.0], label="s", output_dir=str(tmp_path))
        assert isinstance(result, ChartResult)
        assert Path(result.path).exists()


class TestHistogramRender:
    def test_basic(self, tmp_path: Path):
        result = histogram.render([1.0, 2.0, 2.0, 3.0, 4.0], label="dist", output_dir=str(tmp_path))
        assert Path(result.path).exists()


class TestSelector:
    def test_small_uses_bar(self, tmp_path: Path):
        result = selector.select_and_render([1.0, 2.0], output_dir=str(tmp_path))
        assert "bar" in result.path.lower()

    def test_large_uses_line(self, tmp_path: Path):
        result = selector.select_and_render([float(i) for i in range(10)], output_dir=str(tmp_path))
        assert "line" in result.path.lower()


class TestPngWriter:
    def test_writes_valid_png_header(self, tmp_path: Path):
        target = tmp_path / "p.png"
        _png_writer.write_placeholder_png(str(target))
        assert target.exists()
        assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
