"""Canonical text extraction from a source XML file.

Walks the XML applying the policy's include/exclude/strip-keep rules.
Returns an ordered list of (section_ref, normalized_text) pairs.

This is the canonical side of the integrity comparison. The same input
XML under the same policy always produces the same output.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from .normalize import normalize_text
from .policy import Policy


TEI_NS = "{http://www.tei-c.org/ns/1.0}"


@dataclass(frozen=True)
class Section:
    """One addressable unit of canonical text.

    `ref` is the work-internal address (e.g. "1.5" for book 1 line 5,
    or "1.2.3" for section-numbered prose). `text` is the canonical
    text with normalization already applied.
    """
    ref: str
    text: str


def extract_canonical_text(xml_path: Path, policy: Policy) -> list[Section]:
    """Walk the XML at `xml_path` and produce ordered (ref, text) sections.

    Sections are emitted in document order. Empty sections (text was all
    excluded content) are filtered out.
    """
    try:
        tree = ET.parse(str(xml_path))
    except ET.ParseError as e:
        raise RuntimeError(f"XML parse error in {xml_path}: {e}") from e

    root = tree.getroot()
    # Strip namespaces for simpler traversal — common pattern in this codebase.
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]

    body = _find_body(root)
    if body is None:
        return []

    out: list[Section] = []
    for sec_elem, ref in _iter_addressable_leaves(body, policy):
        text = _gather_text(sec_elem, policy)
        text = normalize_text(text, policy.normalization)
        if text:
            out.append(Section(ref=ref, text=text))
    return out


# --- helpers -------------------------------------------------------------

def _find_body(root) -> ET.Element | None:
    """Find the body element. Different TEI files use different structures."""
    for tag in ("body", "text"):
        elem = root.find(f".//{tag}")
        if elem is not None:
            return elem
    # Fall back to <div type="edition"> if no body
    for div in root.iter("div"):
        if div.get("type") == "edition":
            return div
    return None


def _iter_addressable_leaves(body, policy):
    """Yield (leaf_elem, ref_string) pairs in document order.

    "Addressable leaf" is whichever unit the work uses for its primary
    addressing scheme:
    - Line-based (Homer, drama): each <l n="..."> is a leaf
    - Section-based (prose): each leaf <div type="textpart"> is a leaf
    - Mixed: prefer <l> when present; otherwise fall back to leaf <div>

    The ref string is composed from ancestor structural divs' n attributes
    + the leaf's own n.

    For Phase 0 this implementation is intentionally simple. Phase 1 will
    refine per-corpus addressing logic via the policy.
    """
    # Detect what addressing the body uses by what's actually inside it.
    has_l_tags = any(_is_line_elem(d) for d in body.iter())
    if has_l_tags:
        yield from _iter_line_leaves(body, policy)
    else:
        yield from _iter_section_leaves(body, policy)


def _is_line_elem(el):
    """True for <l n="..."> line elements."""
    return el.tag == "l" and el.get("n") is not None


def _iter_line_leaves(body, policy):
    """Iterate <l n="..."> elements with their ancestor book context."""
    # Walk the tree maintaining a stack of (subtype, n) for structural divs.
    stack: list[tuple[str, str]] = []
    yield from _walk_lines(body, stack, policy)


def _walk_lines(elem, stack, policy):
    pushed = False
    if elem.tag == "div" and elem.get("type") == "textpart":
        subtype = elem.get("subtype", "")
        n = elem.get("n", "")
        if subtype and n:
            stack.append((subtype, n))
            pushed = True
    if _is_line_elem(elem):
        n = elem.get("n", "")
        ref_parts = [v for _, v in stack] + [n]
        yield elem, ".".join(ref_parts)
    else:
        for child in elem:
            yield from _walk_lines(child, stack, policy)
    if pushed:
        stack.pop()


def _iter_section_leaves(body, policy):
    """For section-addressed works: yield each leaf textpart div with its
    composed ref."""
    stack: list[tuple[str, str]] = []
    yield from _walk_sections(body, stack, policy)


def _walk_sections(elem, stack, policy):
    pushed = False
    is_textpart_div = (
        elem.tag == "div"
        and elem.get("type") == "textpart"
    )
    if is_textpart_div:
        n = elem.get("n", "") or _autogen_n(elem, stack)
        subtype = elem.get("subtype", "")
        stack.append((subtype, n))
        pushed = True
        # A textpart div is a "leaf" iff it contains no other textpart divs.
        is_leaf = not any(
            child.tag == "div" and child.get("type") == "textpart"
            for child in elem.iter() if child is not elem
        )
        if is_leaf:
            ref = ".".join(v for _, v in stack)
            yield elem, ref
            stack.pop()
            return
    for child in elem:
        yield from _walk_sections(child, stack, policy)
    if pushed:
        stack.pop()


def _autogen_n(elem, stack) -> str:
    """Best-effort synthetic n for divs without one. Uses document position
    so it stays deterministic across runs."""
    parent_str = "_".join(v for _, v in stack) if stack else "root"
    return f"{parent_str}.div"  # caller will append in walk


def _gather_text(elem, policy: Policy) -> str:
    """Concatenate the text content of `elem`'s subtree, applying the policy.

    Rules:
    - elem.tag in policy.exclude → emit nothing (skip subtree entirely,
      do not emit the element's tail either — the tail belongs to the next
      sibling's context)
    - elem.tag in policy.strip_keep_text → traverse children normally,
      no special handling of the element wrapper
    - <gap reason="..."/> → emit policy.gap_marker, do not recurse
    - <choice><orig/><reg/></choice> → resolve per policy.choice_handling
    - <supplied> → handled per policy.supplied_handling
    - default → emit element.text, recurse into children, then emit each
      child's tail in document order

    Tail-text handling is the most subtle part. Each element's `tail` is the
    text that follows its closing tag, BEFORE the next sibling. When we skip
    an element entirely (excluded), we must NOT skip its tail — that tail
    is part of the parent's text content, sitting between the excluded child
    and the next sibling.
    """
    return "".join(_emit_text(elem, policy))


def _emit_text(elem, policy: Policy):
    """Generator of text fragments for an element subtree."""
    if elem.tag in policy.exclude:
        return  # subtree dropped; tail is handled by the caller

    # <gap reason="..."/> — emit a marker
    if elem.tag == "gap":
        if policy.gap_marker:
            yield policy.gap_marker
        return

    # <choice><orig/><reg/></choice> — pick per policy
    if elem.tag == "choice":
        yield from _emit_choice(elem, policy)
        return

    # Normal element. Emit its leading text, walk children, emit each
    # child's tail, then return. We do NOT emit our own tail here — the
    # caller (our parent) emits that after our subtree.
    if elem.text:
        yield elem.text
    for child in elem:
        yield from _emit_text(child, policy)
        # Always emit tail of child, even if child was excluded.
        if child.tail:
            yield child.tail


def _emit_choice(elem, policy: Policy):
    """Resolve a <choice> element per policy.choice_handling."""
    mode = policy.choice_handling  # 'orig' | 'reg' | 'both'
    orig = next((c for c in elem if c.tag == "orig"), None)
    reg = next((c for c in elem if c.tag == "reg"), None)

    if mode == "orig" and orig is not None:
        yield from _emit_text(orig, policy)
    elif mode == "reg" and reg is not None:
        yield from _emit_text(reg, policy)
    elif mode == "both":
        if orig is not None:
            yield from _emit_text(orig, policy)
        if reg is not None:
            yield from _emit_text(reg, policy)
    else:
        # Fallback: pick whichever is present
        for child in elem:
            yield from _emit_text(child, policy)
            if child.tail:
                yield child.tail
