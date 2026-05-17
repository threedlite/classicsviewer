"""Text normalization applied identically on canonical and DB sides.

Whatever normalization is applied must be the same on both sides of the
hash comparison, otherwise pure-format differences produce false positives.
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass


# Common zero-width / formatting characters that should be stripped.
_ZERO_WIDTH = "".join([
    "​",  # zero-width space
    "‌",  # zero-width non-joiner
    "‍",  # zero-width joiner
    "‎",  # left-to-right mark
    "‏",  # right-to-left mark
    "﻿",  # BOM / zero-width no-break space
])
_ZERO_WIDTH_RE = re.compile(f"[{_ZERO_WIDTH}]")


@dataclass(frozen=True)
class NormalizationPolicy:
    """Per-policy normalization knobs.

    Default values match what almost every TEI consumer wants: Unicode NFC,
    whitespace collapsed, NBSP folded to a regular space, zero-width chars
    stripped. Sub-policies can override.
    """
    unicode_form: str = "NFC"       # NFC | NFD | NFKC | NFKD | "none"
    collapse_whitespace: bool = True
    strip_outer: bool = True
    treat_nbsp_as_space: bool = True
    strip_zero_width: bool = True
    case_fold: bool = False         # almost never useful — case is content


_DEFAULT_POLICY = NormalizationPolicy()


def normalize_text(text: str, pol: NormalizationPolicy = _DEFAULT_POLICY) -> str:
    """Apply the given normalization policy to text.

    Returns a string suitable for hashing or comparison. Identical input
    text under identical policy always produces identical output.
    """
    if not text:
        return ""
    if pol.unicode_form != "none":
        text = unicodedata.normalize(pol.unicode_form, text)
    if pol.treat_nbsp_as_space:
        text = text.replace(" ", " ")
    if pol.strip_zero_width:
        text = _ZERO_WIDTH_RE.sub("", text)
    if pol.collapse_whitespace:
        text = re.sub(r"\s+", " ", text)
    if pol.strip_outer:
        text = text.strip()
    if pol.case_fold:
        text = text.casefold()
    return text
