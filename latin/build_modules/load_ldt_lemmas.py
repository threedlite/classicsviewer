#!/usr/bin/env python3
"""
Load Perseus Latin Dependency Treebank form->lemma pairs into `lemma_map`.

Source: data-sources/treebank_data/v2.1/Latin/texts/*.xml
        CC BY-SA 3.0 US, Copyright 2014 The Perseus Digital Library, Tufts
        University. Credited in LicenseActivity.kt and LicenseView.swift.

WHY THIS EXISTS
---------------
Whitaker's Words handles Latin's irregular verbs in PROGRAM CODE, not in its
data files. `DICTLINE.GEN` and `UNIQUES.LAT` contain no paradigm for `sum`, so a
pipeline that derives morphology from those files alone has no route from `est`
to `sum` at all. Measured on the extended DB before this loader:

    est    55,883 tokens  ->  "eject/emit"   (fell through to the stem `ed`, edo)
    esse   21,443         ->  "eject/emit"
    sunt   13,933         ->  ???            (no route whatsoever)
    sit    10,412         ->  "situation, position, site"
    erat    7,450         ->  a stray <orth> inside L&S's `hic` article

~123,000 tokens of the commonest verb in the language, wrong or blank.

The treebank has the answer, at near-total annotator agreement:

    est/sunt/esse/erat/erit/sit/fuit/erant/essent  ->  sum   (0.99-1.00)
    potest -> possum   vult -> volo   fert -> fero   it/ire -> eo

It is already parsed by `interlinear/latin_treebank_loader.py` and already
supplies the lemmas the interlinear DISPLAYS - the gap is that those lemmas
never reached `lemma_map`, so the dictionary layer could not see them.

Morpheus was evaluated as an alternative and rejected: MPL 2.0 makes a shipped
derived table a likely derivative work, and its flat files cover LESS than the
treebank (no `fuit`, `fert`, `ire`).

CONFIDENCE
----------
The annotator agreement share, 0.80-1.00. Whitaker's rows span 0.65-0.95, so a
form the treebank is unanimous about outranks Whitaker's generated possibility,
while an 80%-agreement form sits mid-pack. That ordering is the point: attested
usage should beat generated possibility in proportion to how consistently it was
actually attested.

This loader ADDS a source. It never edits or deletes Whitaker rows.
"""

import sys
from pathlib import Path
from typing import Dict

SOURCE_NAME = "Perseus LDT"

# Measured floor. The treebank yields 18,393 form->lemma pairs at the 0.8
# agreement threshold, from 67,039 annotated tokens across 12 works. A large
# shortfall means a truncated or missing checkout, which must fail the build
# rather than quietly shipping Latin without irregular verbs (CLAUDE.md).
EXPECTED_MIN_PAIRS = 15000


def load_ldt_lemmas(cursor) -> Dict[str, int]:
    """Insert treebank form->lemma rows into `lemma_map`. Returns a stats dict."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / "interlinear"))
    from latin_treebank_loader import LdtLexicon  # noqa: E402

    print("\n=== LOADING PERSEUS LATIN DEPENDENCY TREEBANK LEMMAS ===")
    lex = LdtLexicon()
    lex.load()
    stats = dict(lex.stats)
    print(f"  Parsed {stats.get('tokens', 0):,} annotated tokens, "
          f"{stats.get('forms', 0):,} distinct forms")
    print(f"  Kept {stats.get('kept', 0):,} at >= "
          f"{stats.get('min_agreement_pct', 80)}% annotator agreement")

    if len(lex._lemma) < EXPECTED_MIN_PAIRS:
        raise ValueError(
            f"Perseus LDT yielded only {len(lex._lemma):,} form->lemma pairs, "
            f"below the {EXPECTED_MIN_PAIRS:,} floor (measured 18,393). The "
            f"treebank checkout under data-sources/treebank_data/ is probably "
            f"incomplete. Latin's irregular verbs depend on this."
        )

    # Only insert where Whitaker's existing route leads to an UNRELATED word.
    #
    # A treebank row outranks Whitaker's (0.80-1.00 vs 0.65-0.95), so inserting
    # unconditionally DISPLACES working routes with dead ones. Measured: `se`
    # resolves via Whitaker's stem `s` to a correct "him/her/it/ones-self",
    # while the treebank says `sui` -- which has no Whitaker entry at all, so
    # the join fails, the lookup synthesises "form of sui", and the gloss
    # degrades to L&S's "Aside, by itself".
    #
    # Whitaker stems are PREFIXES of the word they belong to, so the two
    # vocabularies naming the same word share a prefix (`s`/`sui`, `qu`/`qui`,
    # `ill`/`ille`). A genuine error does not (`edo`/`sum`, `e`/`jam`). That
    # prefix relation is the discriminator, and it is a string property of the
    # data, not a list of words.
    from latin_normalization import normalize_latin_headword as _N

    existing = {}
    cursor.execute("SELECT word_form, lemma FROM lemma_map WHERE source LIKE 'Whitaker%'")
    for wf, lem in cursor.fetchall():
        existing.setdefault(wf, set()).add(lem)

    def _related(a, b):
        a, b = _N(a or "").lower(), _N(b or "").lower()
        return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))

    rows = []
    skipped_related = 0
    for surface, lemma in lex._lemma.items():
        prior = existing.get(surface)
        if prior and any(_related(p, lemma) for p in prior):
            skipped_related += 1
            continue
        readings = lex.readings_for(surface) or []
        share = readings[0][2] if readings else 1.0
        upos = readings[0][1] if readings else None
        rows.append((surface, lemma, round(float(share), 4), SOURCE_NAME, upos))
    stats["skipped_whitaker_agrees"] = skipped_related
    print(f"  Skipped {skipped_related:,} forms where Whitaker's stem already "
          f"names the same word")

    cursor.executemany(
        "INSERT INTO lemma_map (word_form, lemma, confidence, source, morph_info) "
        "VALUES (?, ?, ?, ?, ?)", rows)

    stats["rows_inserted"] = len(rows)
    print(f"  Inserted {len(rows):,} treebank form->lemma rows "
          f"(source '{SOURCE_NAME}')")
    return stats
