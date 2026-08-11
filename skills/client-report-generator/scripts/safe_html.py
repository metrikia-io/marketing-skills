#!/usr/bin/env python3
"""
HTML escaping for every untrusted value that reaches the report.

The report is explicitly built to be forwarded to a client or a boss. That makes
it a delivery vehicle: anything that reaches the page and is not escaped runs in
the recipient's browser, not the author's. The untrusted inputs are the ad and
store exports (campaign names, referrers), the account name passed on the command
line, and the narrative markdown. A campaign literally named
`<script>...</script>` - whether by accident or by someone who wants to reach the
agency's client through the agency - must render as text, never execute.

The rule is one-directional and absolute: escape at the point of insertion into
HTML, never trust that a value was clean upstream.
"""

import html

# The only inline tags the narrative may carry. Everything else is escaped.
_ALLOWED_INLINE = ("strong", "em")


def esc(value):
    """Escape a value for insertion as HTML text or an attribute.

    Quotes are escaped too, so the same function is safe inside attributes.
    """
    return html.escape("" if value is None else str(value), quote=True)


def narrative_to_html(markdown, heading_tag="h2"):
    """Render the narrative as a small, closed subset of markdown.

    The narrative is written by the assistant, not the user, but it quotes numbers
    and campaign names lifted from untrusted data, so it is treated as untrusted
    all the same. Everything is escaped first; then a fixed set of block shapes
    (heading, bullet list, paragraph) and two inline emphases are re-introduced
    from the escaped text. Nothing the input contains can produce a tag that was
    not on this list.
    """
    if not markdown or not markdown.strip():
        return ""
    blocks = []
    for chunk in markdown.strip().split("\n\n"):
        text = chunk.strip()
        if not text:
            continue
        blocks.append(_render_block(text, heading_tag))
    return "".join(blocks)


def _render_block(text, heading_tag):
    if text.startswith("## "):
        return f"<{heading_tag}>{_inline(text[3:])}</{heading_tag}>"
    if text.startswith("- "):
        items = "".join(f"<li>{_inline(item)}</li>" for item in _list_items(text))
        return f"<ul>{items}</ul>"
    return f"<p>{_inline(text)}</p>"


def _list_items(text):
    """Split a bullet block into items, folding wrapped lines into their own item.

    Markdown wraps: a bullet longer than the line width continues on the next,
    indented line. Keeping only the lines that start with "- " silently truncated
    every such bullet mid-sentence, and silently is the dangerous part, because the
    report still looked finished and went out to a client that way.
    """
    items = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:])
        elif stripped and items:
            items[-1] += " " + stripped
    return items


def _inline(text):
    """Escape, then re-enable **bold** and *italic* on the escaped text only."""
    safe = esc(text)
    safe = _reintroduce(safe, "**", "strong")
    safe = _reintroduce(safe, "*", "em")
    return safe


def _reintroduce(safe_text, marker, tag):
    """Wrap each matched pair of a marker in a tag, on already-escaped text.

    Escaping first means the only tag this can emit is the one it is handed. An
    odd, unpaired marker is left as literal text: only complete pairs open and
    close a tag, so the output is always balanced.
    """
    parts = safe_text.split(marker)
    pairs = (len(parts) - 1) // 2
    if pairs == 0:
        return safe_text
    out = [parts[0]]
    for index in range(1, len(parts)):
        if index <= pairs * 2 and index % 2 == 1:
            out.append(f"<{tag}>{parts[index]}")
        elif index <= pairs * 2:
            out.append(f"</{tag}>{parts[index]}")
        else:  # leftover unpaired marker, restore it literally
            out.append(f"{marker}{parts[index]}")
    return "".join(out)
