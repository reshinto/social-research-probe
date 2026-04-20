"""Contract: every doc under docs/ has a breadcrumb to docs/README.md and is reachable from it."""

from __future__ import annotations

import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
ROOT_README = Path(__file__).parent.parent.parent / "README.md"
HUB = DOCS_DIR / "README.md"

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _docs_mds() -> list[Path]:
    """All .md files directly under docs/ (not in subdirectories like diagrams/src/)."""
    return [p for p in DOCS_DIR.glob("*.md")]


def _hub_text() -> str:
    return HUB.read_text()


def _internal_links(text: str, base: Path) -> list[Path]:
    """Resolve relative markdown links in text relative to base directory."""
    links = []
    for _label, href in _LINK_RE.findall(text):
        if href.startswith("http") or href.startswith("#"):
            continue
        # strip anchor
        href = href.split("#")[0]
        if not href:
            continue
        resolved = (base / href).resolve()
        links.append(resolved)
    return links


def test_every_doc_is_reachable_from_hub() -> None:
    hub_text = _hub_text()
    hub_links = _internal_links(hub_text, DOCS_DIR)
    unreachable = []
    for doc in _docs_mds():
        if doc == HUB:
            continue
        if doc.resolve() not in hub_links:
            unreachable.append(doc.name)
    assert unreachable == [], f"Docs not linked from docs/README.md: {unreachable}"


def test_every_doc_has_breadcrumb_to_hub() -> None:
    missing = []
    for doc in _docs_mds():
        if doc == HUB:
            continue
        text = doc.read_text()
        if "README.md" not in text and "docs/README.md" not in text:
            missing.append(doc.name)
    assert missing == [], f"Docs missing breadcrumb to docs/README.md: {missing}"


def test_root_readme_links_to_docs_hub() -> None:
    root_text = ROOT_README.read_text()
    assert "docs/README.md" in root_text or "docs/" in root_text, (
        "Root README.md does not link to the docs hub"
    )


def test_all_internal_links_resolve() -> None:
    broken = []
    for doc in _docs_mds():
        for target in _internal_links(doc.read_text(), DOCS_DIR):
            if not target.exists():
                broken.append(f"{doc.name} → {target}")
    assert broken == [], f"Broken internal links: {broken}"
