"""Contracts for docs diagram sources, renders, and references."""

from __future__ import annotations

from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
DIAGRAMS_DIR = DOCS_DIR / "diagrams"
DIAGRAMS_SRC_DIR = DIAGRAMS_DIR / "src"


def _all_svg_names() -> list[str]:
    return [p.name for p in DIAGRAMS_DIR.glob("*.svg")]


def _all_mmd_names() -> list[str]:
    return [p.name for p in DIAGRAMS_SRC_DIR.glob("*.mmd")]


def _all_md_text() -> str:
    return "\n".join(p.read_text() for p in DOCS_DIR.rglob("*.md"))


def test_every_svg_is_referenced_in_a_doc() -> None:
    md_text = _all_md_text()
    unreferenced = [name for name in _all_svg_names() if name not in md_text]
    assert unreferenced == [], f"SVGs not referenced in any doc: {unreferenced}"


def test_every_mmd_has_matching_svg() -> None:
    svg_names = set(_all_svg_names())
    missing = [
        name.replace(".mmd", ".svg")
        for name in _all_mmd_names()
        if name.replace(".mmd", ".svg") not in svg_names
    ]
    assert missing == [], f"Mermaid sources missing rendered SVGs: {missing}"


def test_every_svg_has_matching_mmd() -> None:
    mmd_names = set(_all_mmd_names())
    orphaned = [name for name in _all_svg_names() if name.replace(".svg", ".mmd") not in mmd_names]
    assert orphaned == [], f"Rendered SVGs missing Mermaid sources: {orphaned}"


def test_diagrams_directory_is_non_empty() -> None:
    assert _all_svg_names(), "No SVG files found under docs/diagrams/"
