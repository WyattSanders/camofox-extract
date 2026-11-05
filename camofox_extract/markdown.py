"""Convert Camofox accessibility tree snapshots to clean markdown.

The Camofox snapshot uses an indented tree format::

    - heading "Title" [level=1]
    - paragraph: Some text content here
    - paragraph:
      - link "Click here" [e5]:
        - /url: https://example.com
    - text: "inline text"
    - img
      - /url: https://example.com/image.png

Strategy: process lines sequentially. Container nodes (table, row, cell,
paragraph) are transparent — their children produce the actual content.
Leaf nodes (heading, link, text, img) emit markdown.
"""

from __future__ import annotations

import re
from typing import Optional


def _parse_line(line: str) -> Optional[dict]:
    """Parse a single accessibility tree line.

    Returns {'indent', 'type', 'text', 'attrs'} or None.
    """
    stripped = line.rstrip()
    if not stripped:
        return None

    indent = len(stripped) - len(stripped.lstrip())

    # - type: unquoted text (leaf paragraph/text with content).
    # Checked first so text that itself ends in ":" ("- text: Note:") is kept.
    m = re.match(r'^\s*-\s+(\w+):\s*(.+?)\s*$', stripped)
    if m:
        return {"indent": indent, "type": m.group(1), "text": m.group(2).strip(), "attrs": {}}

    # - type "text" [attrs]:  (colon = has children)
    m = re.match(r'^\s*-\s+(\w+)(?:\s+"([^"]*)")?\s*(.*?)\s*:\s*$', stripped)
    if m:
        return {"indent": indent, "type": m.group(1), "text": m.group(2) or "", "attrs": _attrs(m.group(3))}

    # - type "text" [attrs] (no colon, leaf)
    m = re.match(r'^\s*-\s+(\w+)(?:\s+"([^"]*)")?\s*(.*?)\s*$', stripped)
    if m:
        return {"indent": indent, "type": m.group(1), "text": m.group(2) or "", "attrs": _attrs(m.group(3))}

    # - /url: https://...
    m = re.match(r'^\s*-\s+/url:\s*(.*)', stripped)
    if m:
        return {"indent": indent, "type": "_url", "text": m.group(1).strip(), "attrs": {}}

    return None


def _attrs(s: str) -> dict:
    return {m.group(1): m.group(2) for m in re.finditer(r'\[(\w+)=(.*?)\]', s or "")}


def _strip_q(t: str) -> str:
    return t[1:-1] if t.startswith('"') and t.endswith('"') else t


# Container node types — transparent, produce no output themselves
_CONTAINERS = {"table", "rowgroup", "row", "thead", "tbody", "cell", "list", "listitem"}


def accessibility_tree_to_markdown(snapshot_text: str) -> str:
    """Convert a Camofox accessibility tree snapshot to clean markdown."""
    if not snapshot_text or not snapshot_text.strip():
        return ""

    lines = snapshot_text.split("\n")
    out: list[str] = []
    para: list[str] = []

    def flush():
        if para:
            t = re.sub(r'\s+', ' ', " ".join(para)).strip()
            if t:
                out.append(t)
                out.append("")
            para.clear()

    # Track indent stack for link URLs
    # When we see a link, we remember it; when we see /url at deeper indent, it belongs to the link
    pending_url: list[str] = []  # stack of pending URLs
    link_text: list[str] = []   # stack of link display texts
    in_link_indent = -1

    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1

        if not line.strip():
            flush()
            continue

        # Parse the unstripped line so node["indent"] is the real nesting
        # depth; the link/img look-ahead relies on it to stop at siblings.
        node = _parse_line(line)
        if node is None:
            flush()
            continue

        ntype = node["type"]
        text = _strip_q(node["text"])
        indent = node["indent"]

        # --- URL child: attach to nearest pending link ---
        if ntype == "_url":
            if link_text:
                # This URL belongs to the most recent link
                pending_url.append(text)
            continue

        # --- HEADINGS ---
        if ntype == "heading":
            flush()
            level = int(node["attrs"].get("level", "2") or "2")
            if text:
                out.append(f"{'#' * min(level, 6)} {text}")
                out.append("")
            continue

        # --- LINKS ---
        if ntype == "link":
            flush()
            # Check if next non-empty line is /url at deeper indent
            # If so, the URL will be picked up by the _url handler
            # For now, store the link text and wait for URL
            if text:
                link_text.append(text)
                # Peek ahead for /url
                url_found = False
                j = i
                while j < len(lines):
                    nxt = lines[j].strip()
                    if not nxt:
                        j += 1
                        continue
                    nxt_indent = len(lines[j]) - len(lines[j].lstrip())
                    if nxt_indent <= indent:
                        break
                    if nxt.startswith("- /url:"):
                        url = nxt[len("- /url:"):].strip()
                        out.append(f"[{text}]({url})")
                        out.append("")
                        url_found = True
                        i = j + 1  # skip past the /url line
                        link_text.pop()
                        break
                    j += 1
                if not url_found:
                    # No URL found, just output the text
                    out.append(text)
                    out.append("")
                    link_text.pop()
            continue

        # --- IMAGES ---
        if ntype in ("img", "image"):
            flush()
            url = ""
            j = i
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                nxt_indent = len(lines[j]) - len(lines[j].lstrip())
                if nxt_indent <= indent:
                    break
                if nxt.startswith("- /url:"):
                    url = nxt[len("- /url:"):].strip()
                    i = j + 1
                    break
                j += 1
            if url:
                out.append(f"![{text}]({url})" if text else f"![]({url})")
                out.append("")
            continue

        # --- PARAGRAPHS — transparent container, but text after colon is content ---
        if ntype == "paragraph":
            if text:
                para.append(text)
            continue

        # --- TEXT NODES — inline content ---
        if ntype in ("text", "statictext", "StaticText"):
            if text:
                para.append(text)
            continue

        # --- TABLE STRUCTURE — transparent ---
        if ntype in _CONTAINERS:
            # Cell text that's just a label (like "1.", "upvote") — skip
            # Cell text with real content — add to para
            # But actually, let children handle it
            continue

        # --- SEPARATORS ---
        if ntype in ("separator", "hr"):
            flush()
            out.append("---")
            out.append("")
            continue

        # --- GENERIC with text ---
        if text:
            para.append(text)

    flush()

    result = "\n".join(out)
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    result = "\n".join(ln.rstrip() for ln in result.split("\n"))
    return result.strip()
