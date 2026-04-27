"""Histogram renderer with mean and median markers.

Used to show the distribution shape of a numeric series — is it
symmetric, skewed, bimodal? Mean and median vertical lines make it easy
to see central tendency and skew at a glance.
"""

from __future__ import annotations

import statistics
import tempfile

from social_research_probe.technologies.charts import ChartResult


def _render_with_matplotlib(
    data: list[float], path: str, label: str, bins: int
) -> tuple[float, float]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mean_val = statistics.mean(data) if data else 0.0
    median_val = statistics.median(data) if data else 0.0
    fig = plt.figure()
    plt.hist(data, bins=bins, color="steelblue", edgecolor="black", alpha=0.75)
    plt.axvline(mean_val, color="red", linestyle="--", linewidth=2, label=f"mean={mean_val:.3f}")
    plt.axvline(
        median_val, color="orange", linestyle=":", linewidth=2, label=f"median={median_val:.3f}"
    )
    plt.title(f"Distribution of {label}")
    plt.xlabel(label)
    plt.ylabel("count")
    plt.legend(loc="best")
    plt.savefig(path)
    plt.close(fig)
    return mean_val, median_val


def _sanitise(label: str) -> str:
    return label.replace(" ", "_").replace("/", "_")


def render(
    data: list[float], label: str = "values", output_dir: str | None = None, bins: int = 10
) -> ChartResult:
    """Render a histogram of *data* and return path plus summary caption."""
    save_dir = output_dir if output_dir is not None else tempfile.gettempdir()
    path = f"{save_dir}/{_sanitise(label)}_histogram.png"

    mean_val = 0.0
    median_val = 0.0
    if data:
        try:
            mean_val, median_val = _render_with_matplotlib(data, path, label, bins)
        except Exception:
            from social_research_probe.technologies.charts._png_writer import write_placeholder_png

            write_placeholder_png(path)
    else:
        from social_research_probe.technologies.charts._png_writer import write_placeholder_png

        write_placeholder_png(path)

    return ChartResult(
        path=path,
        caption=(
            f"Histogram: {label} ({len(data)} items, mean={mean_val:.3f}, median={median_val:.3f})"
        ),
    )
