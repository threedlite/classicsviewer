"""Work-specific and author-specific policy resolution registry.

When the generic perseus_standard policy is wrong for a work, add an
override entry here. Phase 0 keeps these minimal (Perseus only); subsequent
phases populate per-corpus entries.

Resolution order (first match wins):
  1. RESOLVER_TABLE — exact work_id match (rare; use sparingly)
  2. AUTHOR_PATTERNS — author prefix match (e.g. tlg0086.* → bekker_milestoned)
  3. CORPUS_SUFFIX_PATTERNS — corpus suffix match (_OGL / _PTA)
  4. default → perseus_standard
"""
from __future__ import annotations


# Exact work_id → sub-policy. Use only when an author needs split-policy
# handling across their works.
RESOLVER_TABLE: dict[str, str] = {
    # Example (commented for later):
    # 'tlg0086.tlg001': 'bekker_milestoned',  # Aristotle Analytica priora
}


# Author prefix → sub-policy. First match wins; order accordingly.
# Phase 0: not yet populated — drama/Aristotle/Plato sub-policies come later.
AUTHOR_PATTERNS: list[tuple[str, str]] = [
    # Phase 1 additions will go here. For Phase 0, perseus_standard handles
    # everything; we add specialized sub-policies as integrity-audit findings
    # demand them.
    # ('tlg0086.', 'bekker_milestoned'),    # Aristotle
    # ('tlg0059.', 'stephanus_milestoned'), # Plato
    # ('tlg0085.', 'drama'),                # Aeschylus
    # ('tlg0006.', 'drama'),                # Euripides
    # ('tlg0011.', 'drama'),                # Sophocles
    # ('tlg0019.', 'drama'),                # Aristophanes
    # ('phi0119.', 'drama'),                # Plautus
    # ('phi0134.', 'drama'),                # Terence
]


# Corpus suffix → sub-policy. Catches the _OGL (First1KGreek) and _PTA
# (Patristic Text Archive) families.
CORPUS_SUFFIX_PATTERNS: list[tuple[str, str]] = [
    # Phase 2 will add these:
    # ('_OGL', 'first1k_standard'),
    # ('_PTA', 'pta_commentary'),
]
