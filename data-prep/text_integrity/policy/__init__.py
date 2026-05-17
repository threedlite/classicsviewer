"""Policy module — defines what counts as canonical source text.

The generic policy is the baseline. Sub-policies (perseus_standard,
bekker_milestoned, etc.) add to / remove from / override the baseline for
specific corpora or work types.

A Policy is resolved per-work via `resolve_policy_for_work(work_id)` which
consults work_overrides.RESOLVER_TABLE (exact match) → AUTHOR_PATTERNS
(author prefix) → CORPUS_SUFFIX_PATTERNS (_OGL / _PTA) → default.

Default fallback is `perseus_standard`.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import importlib

from ..normalize import NormalizationPolicy


# --- Generic baseline ----------------------------------------------------

# Elements whose content is editorial / metadata and should NOT appear in
# canonical source text. These are dropped entirely (no recursion, no tail
# preservation across them).
GENERIC_EXCLUDE = frozenset({
    "teiHeader",
    "note",
    "bibl", "biblScope", "biblStruct", "listBibl",
    "ref", "ptr",
    "gloss",
    "editorialDecl", "fileDesc", "encodingDesc", "profileDesc", "revisionDesc",
    "respStmt", "change",
    "fw",                  # forme work (headers, signatures, catchwords)
    "figDesc", "figure",
    "milestone",           # Plato/Aristotle pagination markers — handled separately if needed
    # apparatus criticus
    "rdg", "witDetail", "witness",
    # source description
    "sourceDesc",
})


# Elements whose own tag is dropped but whose text content is kept.
# Children are walked normally per the include/exclude rules.
GENERIC_STRIP_KEEP_TEXT = frozenset({
    "lem",                 # the lemma reading inside <app>
    "hi", "emph",          # highlighting / emphasis
    "seg",                 # generic segment marker
    "foreign",             # foreign-language insertions
    "label",               # labels (drama speaker labels handled separately)
    "rs",                  # referencing string (e.g. person/place names)
    "name", "persName", "placeName", "orgName", "geogName",
    "date", "num",
    "quote", "q", "cit",   # quotations (the quoted text is content)
    "title",               # work titles cited in running text
    "term",
    "expan",               # expansion of abbreviation — keep the expansion
})


@dataclass
class Policy:
    """Resolved policy for one work. Immutable per-work, looked up once at
    audit time."""
    name: str
    exclude: frozenset[str]
    strip_keep_text: frozenset[str]
    choice_handling: str          # 'orig' | 'reg' | 'both'
    supplied_handling: str        # 'include' | 'mark' | 'exclude'
    gap_marker: str
    addressing: str               # 'line' | 'section' | 'hierarchical'
    normalization: NormalizationPolicy
    _module: Any = field(repr=False, default=None)

    def ref_from_db(self, db_row) -> str:
        """Build the canonical ref string from a DB row joining books+text_lines."""
        if self._module and hasattr(self._module, "ref_from_db"):
            return self._module.ref_from_db(db_row)
        # Default: book.line format
        return f"{db_row['book_number']}.{db_row['line_number']}"


def _resolve_subpolicy_name(work_id: str) -> str:
    """Pick the right sub-policy module name for this work_id."""
    from .work_overrides import (
        RESOLVER_TABLE, AUTHOR_PATTERNS, CORPUS_SUFFIX_PATTERNS,
    )
    if work_id in RESOLVER_TABLE:
        return RESOLVER_TABLE[work_id]
    for prefix, name in AUTHOR_PATTERNS:
        if work_id.startswith(prefix):
            return name
    for suffix, name in CORPUS_SUFFIX_PATTERNS:
        if work_id.endswith(suffix):
            return name
    return "perseus_standard"


def resolve_policy_for_work(work_id: str) -> Policy:
    """Look up the right sub-policy for this work_id and build a Policy
    object that combines the generic baseline with the sub-policy's
    additions / removals / overrides."""
    name = _resolve_subpolicy_name(work_id)
    module = importlib.import_module(f".{name}", package=__name__)

    add_exclude = getattr(module, "ADD_EXCLUDE", frozenset())
    remove_exclude = getattr(module, "REMOVE_EXCLUDE", frozenset())
    exclude = (GENERIC_EXCLUDE | add_exclude) - remove_exclude

    add_strip = getattr(module, "ADD_STRIP_KEEP_TEXT", frozenset())
    remove_strip = getattr(module, "REMOVE_STRIP_KEEP_TEXT", frozenset())
    strip_keep_text = (GENERIC_STRIP_KEEP_TEXT | add_strip) - remove_strip

    return Policy(
        name=name,
        exclude=frozenset(exclude),
        strip_keep_text=frozenset(strip_keep_text),
        choice_handling=getattr(module, "CHOICE_HANDLING", "reg"),
        supplied_handling=getattr(module, "SUPPLIED_HANDLING", "include"),
        gap_marker=getattr(module, "GAP_MARKER", "[…]"),
        addressing=getattr(module, "ADDRESSING", "line"),
        normalization=getattr(module, "NORMALIZATION", NormalizationPolicy()),
        _module=module,
    )
