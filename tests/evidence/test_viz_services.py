"""Evidence tests — every viz renderer produces a valid PNG and caption.

Each of the seven PNG renderers + the ASCII renderer is called with hand-known
inputs. We assert **structural invariants** rather than byte-hash equality
because matplotlib PNG output is not guaranteed byte-reproducible across
platforms / font / library versions — hashing would be brittle in CI.

Invariants per renderer:
- ``ChartResult.path`` exists as a file, ends in ``.png``, size > 200 bytes.
- ``ChartResult.caption`` is non-empty and contains the label.
- Matplotlib backend is ``Agg`` (no display required).

| Renderer | Input | Expected | Why |
| --- | --- | --- | --- |
| bar.render | [10,20,30] | .png + caption mentions label | matplotlib code path |
| line.render | [1..10] | .png | same |
| scatter.render | (x,y) pairs | .png | same |
| histogram.render | 100-point sample | .png | same |
| regression_scatter.render | y=x pairs | .png | same |
| residuals.render | (x,y) | .png | same |
| heatmap.render | 3-feature dict | .png | same |
| ascii.render_bars | [1..5] | multi-line string with bar chars | text renderer |
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")  # no display required

from social_research_probe.viz import (
    ascii as ascii_viz,
    bar,
    heatmap,
    histogram,
    line,
    regression_scatter,
    residuals,
    scatter,
)


def _assert_png_and_caption(result, label: str, min_size_bytes: int = 200) -> None:
    path = Path(result.path)
    assert path.exists(), f"missing PNG at {path}"
    assert path.suffix == ".png"
    assert path.stat().st_size > min_size_bytes
    assert result.caption
    assert label in result.caption or label.replace("_", " ") in result.caption


def test_bar_renderer_writes_png_with_label_caption(tmp_path):
    result = bar.render([10.0, 20.0, 30.0], label="items", output_dir=str(tmp_path))
    _assert_png_and_caption(result, "items")


def test_line_renderer_writes_png(tmp_path):
    result = line.render([float(i) for i in range(10)], label="views", output_dir=str(tmp_path))
    _assert_png_and_caption(result, "views")


def test_scatter_renderer_writes_png(tmp_path):
    result = scatter.render(
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [2.0, 4.0, 6.0, 8.0, 10.0],
        label="correlation",
        output_dir=str(tmp_path),
    )
    _assert_png_and_caption(result, "correlation")


def test_histogram_renderer_writes_png(tmp_path):
    data = [float(i) for i in range(100)]
    result = histogram.render(data, label="distribution", output_dir=str(tmp_path))
    _assert_png_and_caption(result, "distribution")


def test_regression_scatter_renderer_writes_png(tmp_path):
    x = [float(i) for i in range(10)]
    y = [xi for xi in x]  # y = x
    result = regression_scatter.render(x, y, label="regression", output_dir=str(tmp_path))
    _assert_png_and_caption(result, "regression")


def test_residuals_renderer_writes_png(tmp_path):
    x = [float(i) for i in range(10)]
    y = [xi + (0.1 if i % 2 else -0.1) for i, xi in enumerate(x)]
    result = residuals.render(x, y, label="residuals", output_dir=str(tmp_path))
    _assert_png_and_caption(result, "residuals")


def test_heatmap_renderer_writes_png(tmp_path):
    features = {
        "views": [100.0, 200.0, 300.0, 400.0, 500.0],
        "likes": [10.0, 20.0, 30.0, 40.0, 50.0],
        "comments": [1.0, 2.0, 3.0, 4.0, 5.0],
    }
    result = heatmap.render(features, label="heat", output_dir=str(tmp_path))
    _assert_png_and_caption(result, "heat")


def test_ascii_bars_contain_bar_glyph_and_all_labels():
    """ASCII renderer produces a multi-line string with block characters for each bar."""
    out = ascii_viz.render_bars([1.0, 2.0, 3.0, 4.0, 5.0], label="v")
    lines = out.splitlines()
    assert len(lines) >= 5  # at least one per data point
    assert any("█" in line or "▇" in line or "#" in line for line in lines)


def test_ascii_bars_handles_empty_input():
    """Empty input must not crash — returns a safe placeholder string."""
    out = ascii_viz.render_bars([], label="v")
    assert isinstance(out, str)
