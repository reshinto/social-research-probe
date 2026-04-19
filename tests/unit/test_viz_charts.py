"""Tests for the individual chart renderers: line, bar, scatter, and table.

Uses pytest's tmp_path fixture to verify that actual PNG files are written
and that captions carry the expected content. Matplotlib uses the Agg backend
(set in each viz module) so no display is required.
"""

import os
from pathlib import Path

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


# ---------------------------------------------------------------------------
# _render_with_matplotlib — success path via mocked matplotlib
# ---------------------------------------------------------------------------


def _install_fake_matplotlib(monkeypatch):
    """Inject a fake matplotlib and matplotlib.pyplot into sys.modules."""
    import sys
    import types
    import unittest.mock as mock

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


def test_line_render_with_matplotlib_success(monkeypatch, tmp_path):
    """_render_with_matplotlib writes the file when matplotlib is available."""
    from social_research_probe.viz import line as line_mod

    fake_plt = _install_fake_matplotlib(monkeypatch)
    path = str(tmp_path / "out.png")
    line_mod._render_with_matplotlib([1.0, 2.0, 3.0], path, "test")
    fake_plt.savefig.assert_called_once_with(path)


def test_bar_render_with_matplotlib_success(monkeypatch, tmp_path):
    """_render_with_matplotlib writes the file when matplotlib is available."""
    from social_research_probe.viz import bar as bar_mod

    fake_plt = _install_fake_matplotlib(monkeypatch)
    path = str(tmp_path / "out.png")
    bar_mod._render_with_matplotlib([1.0, 2.0], path, "test")
    fake_plt.savefig.assert_called_once_with(path)


def test_scatter_render_with_matplotlib_success(monkeypatch, tmp_path):
    """_render_with_matplotlib writes the file when matplotlib is available."""
    from social_research_probe.viz import scatter as scatter_mod

    fake_plt = _install_fake_matplotlib(monkeypatch)
    path = str(tmp_path / "out.png")
    scatter_mod._render_with_matplotlib([1.0], [2.0], path, "test")
    fake_plt.savefig.assert_called_once_with(path)


def test_table_render_with_matplotlib_success(monkeypatch, tmp_path):
    """_render_with_matplotlib writes the file when matplotlib is available."""
    from social_research_probe.viz import table as table_mod

    fake_plt = _install_fake_matplotlib(monkeypatch)
    path = str(tmp_path / "out.png")
    table_mod._render_with_matplotlib([{"col": "val"}], path, "test")
    fake_plt.savefig.assert_called_once_with(path, bbox_inches="tight")


def test_table_render_with_matplotlib_empty_rows(monkeypatch, tmp_path):
    """_render_with_matplotlib handles empty rows (no col_labels, skips ax.table)."""
    from social_research_probe.viz import table as table_mod

    fake_plt = _install_fake_matplotlib(monkeypatch)
    path = str(tmp_path / "out_empty.png")
    table_mod._render_with_matplotlib([], path, "empty")
    fake_plt.savefig.assert_called_once_with(path, bbox_inches="tight")


def _install_placeholder_writer(monkeypatch):
    calls = []

    def fake_write_placeholder_png(path: str) -> None:
        calls.append(path)
        Path(path).write_bytes(b"png")

    monkeypatch.setattr(
        "social_research_probe.viz._png_writer.write_placeholder_png",
        fake_write_placeholder_png,
    )
    return calls


def test_line_render_falls_back_to_placeholder_on_matplotlib_error(monkeypatch, tmp_path):
    from social_research_probe.viz import line as line_mod

    monkeypatch.setattr(
        line_mod, "_render_with_matplotlib", lambda *args: (_ for _ in ()).throw(RuntimeError)
    )
    calls = _install_placeholder_writer(monkeypatch)

    result = line_mod.render([1.0, 2.0], label="views", output_dir=str(tmp_path))

    assert calls == [result.path]
    assert os.path.isfile(result.path)


def test_bar_render_falls_back_to_placeholder_on_matplotlib_error(monkeypatch, tmp_path):
    from social_research_probe.viz import bar as bar_mod

    monkeypatch.setattr(
        bar_mod, "_render_with_matplotlib", lambda *args: (_ for _ in ()).throw(RuntimeError)
    )
    calls = _install_placeholder_writer(monkeypatch)

    result = bar_mod.render([1.0, 2.0], label="views", output_dir=str(tmp_path))

    assert calls == [result.path]
    assert os.path.isfile(result.path)


def test_scatter_render_falls_back_to_placeholder_on_matplotlib_error(monkeypatch, tmp_path):
    from social_research_probe.viz import scatter as scatter_mod

    monkeypatch.setattr(
        scatter_mod,
        "_render_with_matplotlib",
        lambda *args: (_ for _ in ()).throw(RuntimeError),
    )
    calls = _install_placeholder_writer(monkeypatch)

    result = scatter_mod.render([1.0, 2.0], [3.0, 4.0], label="views", output_dir=str(tmp_path))

    assert calls == [result.path]
    assert os.path.isfile(result.path)


def test_table_render_falls_back_to_placeholder_on_matplotlib_error(monkeypatch, tmp_path):
    from social_research_probe.viz import table as table_mod

    monkeypatch.setattr(
        table_mod,
        "_render_with_matplotlib",
        lambda *args: (_ for _ in ()).throw(RuntimeError),
    )
    calls = _install_placeholder_writer(monkeypatch)

    result = table_mod.render([{"name": "Alice"}], label="scores", output_dir=str(tmp_path))

    assert calls == [result.path]
    assert os.path.isfile(result.path)
