"""Tests for the individual chart renderers: line, bar, scatter, and table.

Uses pytest's tmp_path fixture to verify that actual PNG files are written
and that captions carry the expected content. Matplotlib uses the Agg backend
(set in each viz module) so no display is required.
"""

import os

from social_research_probe.viz.bar import render as bar_render
from social_research_probe.viz.line import render as line_render
from social_research_probe.viz.scatter import render as scatter_render
from social_research_probe.viz.table import render as table_render


def test_line_render_creates_png(tmp_path):
    """line.render should write a PNG file to the specified directory."""
    result = line_render([1.0, 2.0, 3.0, 4.0, 5.0], label="views", output_dir=str(tmp_path))
    assert os.path.isfile(result.path), f"Expected PNG at {result.path}"
    assert result.path.endswith(".png")


def test_bar_render_creates_png(tmp_path):
    """bar.render should write a PNG file to the specified directory."""
    result = bar_render([10.0, 20.0, 30.0], label="items", output_dir=str(tmp_path))
    assert os.path.isfile(result.path), f"Expected PNG at {result.path}"
    assert result.path.endswith(".png")


def test_scatter_render_creates_png(tmp_path):
    """scatter.render should write a PNG file to the specified directory."""
    result = scatter_render(
        [1.0, 2.0, 3.0], [4.0, 5.0, 6.0], label="correlation", output_dir=str(tmp_path)
    )
    assert os.path.isfile(result.path), f"Expected PNG at {result.path}"
    assert result.path.endswith(".png")


def test_table_render_creates_png(tmp_path):
    """table.render should write a PNG file to the specified directory."""
    rows = [{"name": "Alice", "score": "10"}, {"name": "Bob", "score": "8"}]
    result = table_render(rows, label="scores", output_dir=str(tmp_path))
    assert os.path.isfile(result.path), f"Expected PNG at {result.path}"
    assert result.path.endswith(".png")


def test_line_caption_content(tmp_path):
    """line.render caption should mention 'Line chart' and the label."""
    data = [1.0, 2.0, 3.0]
    result = line_render(data, label="engagement", output_dir=str(tmp_path))
    assert "Line chart" in result.caption
    assert "engagement" in result.caption
    assert str(len(data)) in result.caption


def test_bar_caption_content(tmp_path):
    """bar.render caption should mention 'Bar chart' and the label."""
    data = [5.0, 10.0]
    result = bar_render(data, label="clicks", output_dir=str(tmp_path))
    assert "Bar chart" in result.caption
    assert "clicks" in result.caption
    assert str(len(data)) in result.caption
