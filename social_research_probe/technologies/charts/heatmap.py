"""Correlation heatmap renderer.

Takes a mapping of feature-name to numeric series and renders the
pairwise Pearson correlation matrix as a colour-coded grid. Shows every
relationship between features in a single image, so the viewer does not
need to eyeball a dozen separate scatter plots.
"""

from __future__ import annotations

import tempfile

from social_research_probe.technologies.charts.base import ChartResult


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 2 or n != len(b):
        return 0.0
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    num = sum((ai - mean_a) * (bi - mean_b) for ai, bi in zip(a, b, strict=True))
    den_a = sum((ai - mean_a) ** 2 for ai in a)
    den_b = sum((bi - mean_b) ** 2 for bi in b)
    denom = (den_a * den_b) ** 0.5
    return num / denom if denom else 0.0


def _build_matrix(features: dict[str, list[float]]) -> tuple[list[str], list[list[float]]]:
    names = list(features.keys())
    matrix = [[_pearson(features[a], features[b]) for b in names] for a in names]
    return names, matrix


def _render_with_matplotlib(
    names: list[str], matrix: list[list[float]], path: str, label: str
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", color="black", fontsize=8)
    plt.colorbar(im, ax=ax, label="Pearson r")
    ax.set_title(label)
    plt.tight_layout()
    plt.savefig(path)
    plt.close(fig)


def _sanitise(label: str) -> str:
    return label.replace(" ", "_").replace("/", "_")


def render(
    features: dict[str, list[float]],
    label: str = "correlation_heatmap",
    output_dir: str | None = None,
) -> ChartResult:
    """Render a correlation heatmap and return path plus caption."""
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    path = f"{save_dir}/{_sanitise(label)}.png"
    names, matrix = _build_matrix(features) if features else ([], [])

    try:
        _render_with_matplotlib(names, matrix, path, label) if names else None
    except Exception:
        from social_research_probe.technologies.charts._png_writer import write_placeholder_png

        write_placeholder_png(path)
    if not names:
        from social_research_probe.technologies.charts._png_writer import write_placeholder_png

        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=f"Correlation heatmap: {len(names)} features ({label})",
    )
