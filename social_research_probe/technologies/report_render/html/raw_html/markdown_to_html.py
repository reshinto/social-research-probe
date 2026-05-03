"""Minimal Markdown-to-HTML converter for LLM synthesis text.

Handles: headings (mapped up by one level so # → <h2>), bold, italic,
inline code, links, bullet lists, ordered lists, horizontal rules, and
paragraph separation. Intentionally narrow — just enough to render synthesis
LLM output cleanly, not a full CommonMark implementation.
"""

from __future__ import annotations

import html
import re


def md_to_html(text: str) -> str:
    """Convert a Markdown string to an HTML fragment.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            md_to_html(
                text="This tool reduces latency by 30%.",
            )
        Output:
            "<section>Summary</section>"
    """
    lines = text.split("\n")
    output: list[str] = []
    in_list: str | None = None  # "ul" or "ol"

    def close_list() -> None:
        """Document the close list rule at the boundary where callers use it.

        Report rendering has to turn loose research dictionaries into deterministic files, so each
        formatting rule is isolated and easy to review.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                close_list()
            Output:
                None
        """
        nonlocal in_list
        if in_list:
            output.append(f"</{in_list}>")
            in_list = None

    for line in lines:
        # Headings: # maps to <h2>, ## to <h3>, etc. (capped at h6)
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            close_list()
            level = min(len(m.group(1)) + 1, 6)
            output.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            close_list()
            output.append("<hr>")
            continue

        # Bullet list item
        m = re.match(r"^[-*+]\s+(.*)", line)
        if m:
            if in_list == "ol":
                close_list()
            if in_list != "ul":
                output.append("<ul>")
                in_list = "ul"
            output.append(f"<li>{_inline(m.group(1))}</li>")
            continue

        # Ordered list item
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            if in_list == "ul":
                close_list()
            if in_list != "ol":
                output.append("<ol>")
                in_list = "ol"
            output.append(f"<li>{_inline(m.group(1))}</li>")
            continue

        # Blank line — ends a paragraph/list
        if not line.strip():
            close_list()
            output.append("")
            continue

        # Paragraph text
        close_list()
        output.append(f"<p>{_inline(line)}</p>")

    close_list()

    # Collapse consecutive blank lines
    result = "\n".join(output)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def _inline(text: str) -> str:
    """Convert inline Markdown spans (bold, italic, code, links) to HTML.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _inline(
                text="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    # HTML-escape first to protect literal < > & characters
    text = html.escape(text, quote=False)
    # Bold + italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic: *x* or _x_
    text = re.sub(r"\*([^*]+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_([^_]+?)_", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`([^`]+?)`", r"<code>\1</code>", text)
    # Links [label](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}" rel="noopener noreferrer">{m.group(1)}</a>',
        text,
    )
    return text
