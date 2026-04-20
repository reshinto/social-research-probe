"""Contract: every SVG under docs/diagrams/ is referenced by at least one Markdown file under docs/."""

from __future__ import annotations

from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
DIAGRAMS_DIR = DOCS_DIR / "diagrams"


def _all_svg_names() -> list[str]:
    return [p.name for p in DIAGRAMS_DIR.glob("*.svg")]


def _all_md_text() -> str:
    return "\n".join(p.read_text() for p in DOCS_DIR.rglob("*.md"))


def test_every_svg_is_referenced_in_a_doc() -> None:
    md_text = _all_md_text()
    unreferenced = [name for name in _all_svg_names() if name not in md_text]
    assert unreferenced == [], f"SVGs not referenced in any doc: {unreferenced}"


def test_diagrams_directory_is_non_empty() -> None:
    assert _all_svg_names(), "No SVG files found under docs/diagrams/"
