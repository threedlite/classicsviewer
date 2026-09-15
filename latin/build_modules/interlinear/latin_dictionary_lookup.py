#!/usr/bin/env python3
"""
Latin Dictionary Lookup Module

Provides dictionary lookup functionality for Latin words using:
1. Whitaker's Words dictionary entries
2. Latin lemma_map for morphological analysis

Similar to Greek ui_dictionary_lookup.py but adapted for Latin orthography.
"""

import sqlite3
import re
import unicodedata
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple
from functools import lru_cache

# The same normaliser the L&S loader keyed its headwords with. Importing it
# rather than re-deriving the rules is deliberate: two divergent copies is how
# Latin lookup silently half-works (see latin_normalization.py's docstring).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from latin_normalization import (  # noqa: E402
    normalize_latin_headword,
    lemmas_related,
)


@dataclass
class DictionaryEntry:
    """Represents a dictionary entry for Latin."""
    lemma: str
    definition: str
    morph_info: Optional[str] = None
    is_direct_match: bool = False
    confidence: Optional[float] = None
    source: Optional[str] = None


class LatinRepository:
    """Repository for Latin dictionary and morphology lookups."""

    def __init__(self, db_path: str, debug: bool = False):
        self.db_path = db_path
        self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        self.debug = debug

    def normalize_apostrophes(self, word: str) -> str:
        """Normalize all apostrophe variants to U+0027 (standard apostrophe)."""
        return (word
                .replace("'", "'")   # U+0027 APOSTROPHE (no change)
                .replace("\u2019", "'")   # U+2019 RIGHT SINGLE QUOTATION MARK → U+0027
                .replace("ʼ", "'")   # U+02BC MODIFIER LETTER APOSTROPHE → U+0027
                .replace("᾿", "'")   # U+1FBF GREEK PSILI → U+0027
                .replace("᾽", "'")   # U+1FBD GREEK KORONIS → U+0027
                .replace("′", "'")   # U+2032 PRIME → U+0027
                .replace("´", "'"))  # U+00B4 ACUTE ACCENT → U+0027

    # Quotation marks glued to a word by the source markup. `text_lines` keeps
    # the punctuation attached, so the surface reaching the lookup is `“non`,
    # `‘o`, `M’` or `est”`, none of which matches anything and all of which come
    # out blank. Measured on the shipped build: 7,277 blank tokens carry a quote
    # mark, and 3,415 of them resolve immediately once it is removed.
    #
    # Stripped from the ENDS only. Nothing internal is touched, so a word that
    # legitimately contains an apostrophe is unaffected, and a token that is
    # ONLY punctuation (`”` alone, 2,270 tokens) strips to empty and stays
    # blank -- it is not a word and should not acquire a gloss.
    _EDGE_QUOTES = "\u2018\u2019\u201c\u201d\u00ab\u00bb\u2039\u203a\"'\u201a\u201e"

    @classmethod
    def strip_edge_quotes(cls, word: str) -> str:
        """The word without quotation marks at either end."""
        return (word or "").strip(cls._EDGE_QUOTES)

    def normalize_latin(self, word: str) -> str:
        """
        Normalize Latin word for lookup.

        - Normalizes apostrophe variants
        - Removes macrons (ā→a, ē→e, etc.)
        - Converts to lowercase
        - Handles u/v and i/j variants
        """
        # First normalize apostrophes
        word = self.normalize_apostrophes(word)

        # Then normalize to NFD (decomposed form)
        decomposed = unicodedata.normalize('NFD', word)

        # Remove combining characters (macrons, etc.)
        without_diacritics = ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')

        # Convert to lowercase
        lowercased = without_diacritics.lower()

        return lowercased

    def normalize_latin_uv(self, word: str) -> str:
        """Additional normalization for u/v variants."""
        normalized = self.normalize_latin(word)
        # Classical Latin: v→u (e.g., "uirum" for "virum")
        # We try both forms
        return normalized

    # Sources the interlinear glosses from, in the absence of an explicit
    # override. Whitaker's terse "(n.) shore, coast;" shape is what
    # extract_gloss() is built for; a Lewis & Short article fed through it
    # yields the macronised headword or a scrap of etymology.
    #
    # This default exists so that ADDING a dictionary source to the database
    # cannot silently change interlinear output. Before it, step 1 below matched
    # any headword row with no source filter and short-circuited, so the 107,856
    # Lewis & Short rows would have started supplying glosses on the next
    # regeneration with no code change at all.
    # See latin/LATIN_GLOSS_PLAN.md §5.1 and latin/LEWIS_SHORT_PLAN.md §2.3.
    # An imported dictionary package is NOT listed here, and must not be.
    # Measured: adding it to the primary headword match let its entries shadow
    # Whitaker wherever Whitaker files a word under a different citation form.
    # The package has headwords for the prefixes se-, re- and for huc, so
    #   se  15,263 tokens  "him/her/it/ones-self" -> "sine, without, aside"
    #   hoc 13,837         "this"                 -> "to this place, hither"
    #   te  12,991         "you (sing.)"          -> "pronominal suffix"
    #   re   4,100         "thing"                -> "to stand back"
    # ~46,000 tokens of confident nonsense, none of it detectable as suspect
    # because the text is ordinary English. The package is consulted instead
    # where it can only help: to fill a blank, and to supply the lemma the
    # treebank resolved when Whitaker has no entry for it (see the generator).
    GLOSS_PACKAGE_SOURCE = "Lewis & Short glosses"
    DEFAULT_GLOSS_SOURCES = ("Whitaker", "Whitaker UNIQUES")

    # `lemma_map` has NO language column, and the generator runs against the
    # ASSEMBLED database, so a Latin surface form sees every language's
    # mappings. 2,182 Latin surface forms collide with a non-Latin lemma:
    #
    #     lemma_map:  terra -> terr   (Whitaker)
    #                 terra -> terra  (IcePaHC — Old Norse)
    #                 terra -> tāru   (RINAP   — Akkadian)
    #
    # The join then finds no Latin dictionary row for headword "tāru" and the
    # code below synthesises "form of tāru", which shipped as the gloss for
    # *terra* in the Aeneid.
    #
    # The column that DOES identify the language is `source`: every module
    # writes its own distinct strings, and Latin's is exactly one. Verified
    # across the module DBs — latin=Whitaker; greek=oga/wiktionary*/
    # perseus_treebank/...; norse=IcePaHC/Zoega/Thorpe Glossary;
    # old_english=Bosworth-Toller; sanskrit=DCS*; pali=Statistical Dictionary.
    # No string is shared between modules, so this needs no schema change.
    # Latin's own mapping sources. `Whitaker` is the only one present today —
    # Bridge-A (LEWIS_SHORT_PLAN.md §5.2.1) deliberately writes no lemma_map
    # rows, which is why Lewis & Short does not appear in the DB's lemma_map.
    # The other two are listed ANYWAY so that adding them later (Bridge-B, or
    # any future Latin mapping source) cannot be silently filtered out: an
    # unmatched value in an IN clause costs nothing, whereas a missing one
    # would drop rows with no error. Verified against the module DBs: no other
    # language writes any of these strings.
    # "Perseus LDT" carries the treebank's form->lemma pairs, which are the
    # only route from an irregular verb form to its lemma (Whitaker's data
    # files contain no paradigm for sum). Omitting it here would filter those
    # rows straight back out.
    LATIN_LEMMA_SOURCES = ("Whitaker", "Whitaker UNIQUES", "Lewis-Short",
                           "Perseus LDT", GLOSS_PACKAGE_SOURCE)

    def get_all_dictionary_entries(self, word: str, language: str = "latin",
                                   sources: Optional[Tuple[str, ...]] = None
                                   ) -> List[DictionaryEntry]:
        """
        Get all dictionary entries for a Latin word.

        Args:
            sources: restrict to these `dictionary_entries.source` values.
                     None (the default) means DEFAULT_GLOSS_SOURCES.
                     Pass () to search every source.

        Lookup strategy:
        1. Try exact match on headword
        2. Try normalized form (no macrons, lowercase)
        3. Try lemma_map for inflected forms
        4. Try u/v and i/j variants
        5. Try stripping enclitics

        Note: Dictionary entries are sorted by Whitaker's frequency codes during import,
        so the first result for any lemma is the most common meaning.
        """
        entries = []
        cursor = self.conn.cursor()

        # Build the source restriction. Empty tuple => no restriction.
        if sources is None:
            sources = self.DEFAULT_GLOSS_SOURCES
        if sources:
            src_sql = " AND source IN (%s)" % ",".join("?" * len(sources))
            src_params = tuple(sources)
        else:
            src_sql = ""
            src_params = ()

        # Restrict lemma_map to this language's own mappings (see
        # LATIN_LEMMA_SOURCES). Applied only for Latin, so no other language's
        # lookup behaviour can change.
        if language == "latin":
            lm_sql = " AND lm.source IN (%s)" % ",".join(
                "?" * len(self.LATIN_LEMMA_SOURCES))
            lm_params = tuple(self.LATIN_LEMMA_SOURCES)
        else:
            lm_sql = ""
            lm_params = ()

        # Drop quotation marks glued to the ends before anything else, so a
        # quoted word looks up exactly as the bare word does.
        stripped = self.strip_edge_quotes(word)
        if stripped and stripped != word:
            word = stripped

        # Normalize the input word
        word_normalized = self.normalize_latin(word)

        # 1. Try exact match on headword
        cursor.execute("""
            SELECT headword, entry_plain, source
            FROM dictionary_entries
            WHERE headword = ? AND language = ?""" + src_sql + """
            ORDER BY id""",
            (word, language) + src_params)

        for row in cursor.fetchall():
            if row['entry_plain']:
                entries.append(DictionaryEntry(
                    lemma=row['headword'],
                    definition=row['entry_plain'],
                    source=row['source'],
                    is_direct_match=True
                ))

        # 2. Try normalized (lowercase) form on headword if different
        if not entries and word_normalized != word:
            cursor.execute("""
                SELECT headword, entry_plain, source
                FROM dictionary_entries
                WHERE headword = ? AND language = ?""" + src_sql + """
                ORDER BY id""",
                (word_normalized, language) + src_params)

            for row in cursor.fetchall():
                if row['entry_plain']:
                    entries.append(DictionaryEntry(
                        lemma=row['headword'],
                        definition=row['entry_plain'],
                        source=row['source'],
                        is_direct_match=True
                    ))

        # 2b. Case-PRESERVING orthographic normalisation.
        #
        # normalize_latin() lowercases. latin_normalization.py deliberately does
        # not, because proper nouns are legitimately capitalised in both L&S and
        # Whitaker's, and L&S headwords were keyed with that rule. The two never
        # meet: the pipeline lemma "Juno" becomes "juno" then "iuno" at step 4,
        # while the L&S headword is "Iuno". Same for Troja/Troia.
        #
        # This step applies the loader's own rule to the query, so the query key
        # and the stored key are produced by one function. Measured on Vergil,
        # 618 tokens were failing on this mismatch alone (conjunx/coniunx,
        # Juno/Iuno, Troja/Troia, juventus/iuventus, jubeo/iubeo).
        if not entries:
            canonical = normalize_latin_headword(word)
            if canonical and canonical not in (word, word_normalized):
                cursor.execute("""
                    SELECT headword, entry_plain, source
                    FROM dictionary_entries
                    WHERE headword = ? AND language = ?""" + src_sql,
                    (canonical, language) + src_params)
                for row in cursor.fetchall():
                    if row['entry_plain']:
                        entries.append(DictionaryEntry(
                            lemma=row['headword'],
                            definition=row['entry_plain'],
                            source=row['source'],
                            is_direct_match=True
                        ))

        # 2c. Enclitic split, BEFORE lemma_map.
        #
        # `-que` on the end of a word means "and". The split used to be step 6,
        # a last resort reached only when nothing else matched -- and the L&S
        # glosses package contributes lemma_map rows keyed on the WHOLE enclitic
        # surface (`semperque -> semper`, `magisque -> magus/maga/magis`). Those
        # rows satisfy step 3, so the split never ran. Two results, measured on
        # the shipped build: the "+ and" was lost on 21,578 tokens, and where the
        # package offered several lemmas for the surface the selector could take
        # the wrong one -- `magisque` glossed "magian, learned Persian magician".
        # `idque`, which has no lemma_map row at all, reached step 6 and came out
        # right, which is what showed the machinery works when it is allowed to.
        #
        # Runs after the direct-headword steps, so a surface that IS its own
        # headword still wins outright: `neque`, `atque`, `quoque`, `itaque`,
        # `denique` and 47 others (20,650 tokens) are untouched.
        #
        # `-ne` is deliberately NOT handled here. Too many ordinary words end in
        # it (bene, sine, omne, nomine); it stays at the last-resort step below.
        if not entries and language == "latin":
            enclitic_info = self._strip_enclitic(word_normalized)
            if (enclitic_info and enclitic_info[1] != '-ne (?)'
                    and not self._has_fused_enclitic_lemma(word_normalized)):
                base_word, enclitic_meaning = enclitic_info
                for entry in self.get_all_dictionary_entries(
                        base_word, language, sources):
                    entries.append(DictionaryEntry(
                        lemma=entry.lemma,
                        definition=f"{entry.definition} + {enclitic_meaning}",
                        morph_info=entry.morph_info,
                        confidence=entry.confidence,
                        source=entry.source,
                        is_direct_match=False
                    ))

        # 3. Try lemma_map for inflected forms - use indexed lookup only
        if not entries:
            # First try exact match on indexed word_form column
            cursor.execute("""
                SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                       de.entry_plain, de.source as dict_source
                FROM lemma_map lm
                LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?""" + src_sql.replace(' AND source IN', ' AND de.source IN') + """
                WHERE lm.word_form = ?""" + lm_sql + """
                ORDER BY lm.confidence DESC
                -- Raised from 5: POS filtering (select_entry_for_pos) happens
                -- downstream, and a 5-row cut discarded the correct-POS
                -- candidate before it could be considered. `alto` returned five
                -- rows from stem `al` (ala "wing") and none from `alt` (altus
                -- "high"), so the filter had nothing to choose. Ordering is
                -- unchanged, so entries[0] — the legacy fallback — is identical.
                LIMIT 50
            """, (language,) + src_params + (word,) + lm_params)

            for row in cursor.fetchall():
                definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                entries.append(DictionaryEntry(
                    lemma=row['lemma'],
                    definition=definition,
                    morph_info=row['morph_info'],
                    confidence=row['confidence'],
                    source=row['dict_source'] or row['source'],
                    is_direct_match=False
                ))

        # 3b. Try normalized form in lemma_map (lowercase) if different from original
        if not entries and word_normalized != word:
            cursor.execute("""
                SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                       de.entry_plain, de.source as dict_source
                FROM lemma_map lm
                LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?""" + src_sql.replace(' AND source IN', ' AND de.source IN') + """
                WHERE lm.word_form = ?""" + lm_sql + """
                ORDER BY lm.confidence DESC
                -- Raised from 5: POS filtering (select_entry_for_pos) happens
                -- downstream, and a 5-row cut discarded the correct-POS
                -- candidate before it could be considered. `alto` returned five
                -- rows from stem `al` (ala "wing") and none from `alt` (altus
                -- "high"), so the filter had nothing to choose. Ordering is
                -- unchanged, so entries[0] — the legacy fallback — is identical.
                LIMIT 50
            """, (language,) + src_params + (word_normalized,) + lm_params)

            for row in cursor.fetchall():
                definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                entries.append(DictionaryEntry(
                    lemma=row['lemma'],
                    definition=definition,
                    morph_info=row['morph_info'],
                    confidence=row['confidence'],
                    source=row['dict_source'] or row['source'],
                    is_direct_match=False
                ))

        # 3c. Short tokens: retry as a CAPITALISED headword.
        #
        # Roman praenomina are abbreviated to a single letter in the text ("l.
        # Cornelius") but Whitaker stores them capitalised: L = "Lucius", C =
        # "Gaius", T = "Titus", Q = "Quintus", K = "Kaeso", Ti = "Tiberius".
        # Previously these resolved only by accident - lemma_map has no Latin
        # row for "l", but Bosworth-Toller (Old English) maps l -> L, and the
        # join happened to land on the Latin headword. Filtering lemma_map to
        # Latin sources removed that, costing ~229 praenomen glosses.
        #
        # Restricted to tokens of 1-2 characters so it only applies to
        # abbreviations. A length rule, not a word list: it never asks WHICH
        # abbreviation. Longer words keep the existing lowercase-only path, so
        # an ordinary word cannot be pulled onto a proper noun.
        if not entries and 1 <= len(word_normalized) <= 2:
            capitalised = word_normalized.upper() if len(word_normalized) == 1 \
                else word_normalized.capitalize()
            if capitalised != word:
                cursor.execute("""
                    SELECT headword, entry_plain, source
                    FROM dictionary_entries
                    WHERE headword = ? AND language = ?""" + src_sql,
                    (capitalised, language) + src_params)
                for row in cursor.fetchall():
                    if row['entry_plain']:
                        entries.append(DictionaryEntry(
                            lemma=row['headword'],
                            definition=row['entry_plain'],
                            source=row['source'],
                            is_direct_match=True
                        ))

        # 4. Try u/v variants (classical Latin often uses 'u' where medieval uses 'v')
        #
        # Headwords FIRST. "uel" is not a headword but "vel" is, and it is a
        # Latin dictionary entry ("or"). Previously this was found only by
        # accident: lemma_map has no Whitaker row for "vel", only Zoega and
        # IcePaHC (Old Norse) rows, and the join to dictionary_entries happened
        # to land on the Latin headword. Once lemma_map is filtered to Latin
        # sources that route disappears, so 1,459 occurrences of "uel" lost
        # their gloss. Looking the variant up as a headword is what the code
        # should have done all along.
        if not entries:
            for variant in (word_normalized.replace('v', 'u'),
                            word_normalized.replace('u', 'v'),
                            word_normalized.replace('j', 'i'),
                            *self._j_variants(word_normalized),
                            *self._j_variants(word)):
                if variant in (word_normalized, word):
                    continue
                cursor.execute("""
                    SELECT headword, entry_plain, source
                    FROM dictionary_entries
                    WHERE headword = ? AND language = ?""" + src_sql,
                    (variant, language) + src_params)
                for row in cursor.fetchall():
                    if row['entry_plain']:
                        entries.append(DictionaryEntry(
                            lemma=row['headword'],
                            definition=row['entry_plain'],
                            source=row['source'],
                            is_direct_match=True
                        ))
                if entries:
                    break

        if not entries:
            # Try replacing v with u
            word_u = word_normalized.replace('v', 'u')
            if word_u != word_normalized:
                cursor.execute("""
                    SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                           de.entry_plain, de.source as dict_source
                    FROM lemma_map lm
                    LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?""" + src_sql.replace(' AND source IN', ' AND de.source IN') + """
                    WHERE lm.word_form = ?""" + lm_sql + """
                    ORDER BY lm.confidence DESC
                    LIMIT 50
                """, (language,) + src_params + (word_u,) + lm_params)

                for row in cursor.fetchall():
                    definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                    entries.append(DictionaryEntry(
                        lemma=row['lemma'],
                        definition=definition,
                        morph_info=row['morph_info'],
                        confidence=row['confidence'],
                        source=row['dict_source'] or row['source'],
                        is_direct_match=False
                    ))

            # Try replacing u with v
            if not entries:
                word_v = word_normalized.replace('u', 'v')
                if word_v != word_normalized:
                    cursor.execute("""
                        SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                               de.entry_plain, de.source as dict_source
                        FROM lemma_map lm
                        LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?""" + src_sql.replace(' AND source IN', ' AND de.source IN') + """
                        WHERE lm.word_form = ?""" + lm_sql + """
                        ORDER BY lm.confidence DESC
                        LIMIT 50
                    """, (language,) + src_params + (word_v,) + lm_params)

                    for row in cursor.fetchall():
                        definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                        entries.append(DictionaryEntry(
                            lemma=row['lemma'],
                            definition=definition,
                            morph_info=row['morph_info'],
                            confidence=row['confidence'],
                            source=row['dict_source'] or row['source'],
                            is_direct_match=False
                        ))

        # 5. Try i/j variants in lemma_map (j is sometimes used for consonantal i).
        # Both directions: j -> i as before, and the i -> j spellings from
        # _j_variants(), since Whitaker's lemma_map forms are j-spelled.
        if not entries:
            for word_i in [word_normalized.replace('j', 'i'),
                           *self._j_variants(word_normalized), *self._j_variants(word)]:
                if word_i in (word_normalized, word) or entries:
                    continue
                cursor.execute("""
                    SELECT lm.lemma, lm.morph_info, lm.confidence, lm.source,
                           de.entry_plain, de.source as dict_source
                    FROM lemma_map lm
                    LEFT JOIN dictionary_entries de ON lm.lemma = de.headword AND de.language = ?""" + src_sql.replace(' AND source IN', ' AND de.source IN') + """
                    WHERE lm.word_form = ?""" + lm_sql + """
                    ORDER BY lm.confidence DESC
                    LIMIT 50
                """, (language,) + src_params + (word_i,) + lm_params)

                for row in cursor.fetchall():
                    definition = row['entry_plain'] if row['entry_plain'] else f"form of {row['lemma']}"
                    entries.append(DictionaryEntry(
                        lemma=row['lemma'],
                        definition=definition,
                        morph_info=row['morph_info'],
                        confidence=row['confidence'],
                        source=row['dict_source'] or row['source'],
                        is_direct_match=False
                    ))

        # 6. Try stripping Latin enclitics (-que, -ve, -ne)
        if not entries:
            enclitic_info = self._strip_enclitic(word_normalized)
            if enclitic_info:
                base_word, enclitic_meaning = enclitic_info
                # Recursively look up the base word
                base_entries = self.get_all_dictionary_entries(base_word, language)
                if base_entries:
                    # Found the base word - modify the first entry to include enclitic
                    for entry in base_entries:
                        # Prepend the enclitic meaning to the definition
                        modified_def = f"{entry.definition} + {enclitic_meaning}"
                        entries.append(DictionaryEntry(
                            lemma=entry.lemma,
                            definition=modified_def,
                            morph_info=entry.morph_info,
                            confidence=entry.confidence,
                            source=entry.source,
                            is_direct_match=False
                        ))

        return entries

    @staticmethod
    def _j_variants(word: str):
        """Spellings with consonantal i written as j, which is how Whitaker's
        data files spell it: `Juppiter`, `ejusmodi`, `major`, `jam`.

        The existing variant step only went j -> i, so an i-spelled surface
        could never reach a j-spelled Whitaker headword. The L&S gloss package
        had been bridging that gap with rows like `iuppiter -> juppiter`; its
        2026-09-13 revision dropped them and `Iuppiter` (516 tokens) and
        `eiusmodi` (196) went blank. Measured on that build: 182 blank surfaces
        / 1,519 tokens whose j-spelling Whitaker knows.

        Consonantal i is word-initial i before a vowel, or i between vowels.
        Both substitutions are tried, alone and together. No word list.
        """
        out = []
        initial = 'j' + word[1:] if len(word) > 1 and word[0] in 'iI' and word[1].lower() in 'aeiou' else None
        if initial is not None:
            initial = ('J' if word[0] == 'I' else 'j') + word[1:]
        inter = re.sub(r'(?<=[aeiouAEIOU])i(?=[aeiou])', 'j', word)
        for cand in (initial, inter, (re.sub(r'(?<=[aeiouAEIOU])i(?=[aeiou])', 'j', initial) if initial else None)):
            if cand and cand != word and cand not in out:
                out.append(cand)
        return out

    def _has_fused_enclitic_lemma(self, word: str) -> bool:
        """True when a lexicon analyses this surface as ONE word ending in -que.

        In `quisque` ("each") and `uterque` ("both") the -que is part of the
        word, not "and". Splitting them yields "who + and" for `quaeque` and
        "whether + and" for `utrumque`, breaking 3,529 tokens that are correct
        today.

        The test is the lemma the lexicon already recorded, not a list of words:
        a fused form's lemma itself ends in -que (`quaeque -> quisque`,
        `utrumque -> uterque`), while a real enclitic's lemma never does
        (`semperque -> semper`, `magnoque -> magnus`, `iamque -> jam`).

        Known residue: `quamque`, `quidque`, `quantumque`, `quidve` (449 tokens)
        carry no fused lemma in lemma_map, so they still split. Recorded in
        LATIN_GLOSS_PIPELINE.md rather than patched with a word list.

        The bare particle is excluded from the test. The 2026-09-11 gloss
        package records every enclitic surface twice -- `ductoresque -> ductor`
        and `ductoresque -> que (conj)` -- and that second lemma ends in -que
        without being a fused word. Left in, it made this guard true for every
        package-covered enclitic and dropped the "+ and" on 45,346 tokens
        (LSGLOSS_UPDATE_2026-09-11_FINDINGS.md section 3). `que` here is the
        enclitic the guard is about, not a vocabulary word being glossed.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM lemma_map WHERE word_form = ? AND lower(lemma) "
            "LIKE '%que' AND lower(lemma) <> 'que' LIMIT 1", (word.lower(),))
        return cursor.fetchone() is not None

    def _strip_enclitic(self, word: str) -> Optional[tuple]:
        """
        Check if word has a Latin enclitic suffix and return (base_word, enclitic_meaning).

        Common Latin enclitics:
        - -que = "and" (most common)
        - -ve = "or"
        - -ne = interrogative particle (makes a yes/no question)

        Returns None if no enclitic found.
        """
        word_lower = word.lower()

        # Check for -que (and) - most common
        if len(word_lower) > 3 and word_lower.endswith('que'):
            base = word_lower[:-3]
            # Avoid false positives: some words naturally end in -que
            # like 'aeque', 'usque', 'neque', 'atque', 'itaque', 'quoque'
            false_positives = {'aeq', 'usq', 'neq', 'atq', 'itaq', 'quoq', 'ubiq', 'undiq', 'utiq', 'pleriq', 'deniq'}
            if base not in false_positives and len(base) >= 2:
                return (base, '-que (and)')

        # Check for -ve (or)
        if len(word_lower) > 2 and word_lower.endswith('ve'):
            base = word_lower[:-2]
            # Avoid words that naturally end in -ve
            false_positives = {'si', 'ni', 'seu', 'iu'}  # sive, nive, seuve not common
            if base not in false_positives and len(base) >= 2:
                return (base, '-ve (or)')

        # Check for -ne (question marker)
        if len(word_lower) > 2 and word_lower.endswith('ne'):
            base = word_lower[:-2]
            # Many words naturally end in -ne: omne, bene, sine, etc.
            # Only strip if base is substantial and makes sense
            # This is trickier, so we'll be conservative
            false_positives = {'om', 'be', 'si', 'u', 'pla', 'ple'}
            if base not in false_positives and len(base) >= 3:
                return (base, '-ne (?)')

        return None

    def get_morph_info(self, word: str) -> Optional[str]:
        """Get morphological information for a word from lemma_map."""
        cursor = self.conn.cursor()
        word_normalized = self.normalize_latin(word)

        # Try exact match first (uses index)
        cursor.execute("""
            SELECT morph_info FROM lemma_map
            WHERE word_form = ?
            AND morph_info IS NOT NULL AND morph_info != ''
            ORDER BY confidence DESC
            LIMIT 1
        """, (word,))

        row = cursor.fetchone()
        if row:
            return row[0]

        # Try normalized form if different
        if word_normalized != word:
            cursor.execute("""
                SELECT morph_info FROM lemma_map
                WHERE word_form = ?
                AND morph_info IS NOT NULL AND morph_info != ''
                ORDER BY confidence DESC
                LIMIT 1
            """, (word_normalized,))

            row = cursor.fetchone()
            return row[0] if row else None

        return None


# --------------------------------------------------------------------------- #
# POS-aware entry selection
#
# Whitaker's headwords are STEMS, so one key collapses unrelated words:
#   or  = oro "pray" + ora "shore" + uro "burn"
#   al  = ala "wing" + alo "feed" + allium "garlic"
#   alt = altus "high" + altum "the sea"
# The generator used to take entries[0] and never look at the part of speech,
# which is why Aeneid 1.1 glossed `oris` as "rise (sun/river)" and 1.3 glossed
# `alto` as "wing".
#
# Both signals used here are already in the interlinear record, put there by the
# LDT/Stanza pass: the token's UPOS and its lemma. Neither introduces a word
# list — the UPOS map is a closed 13-tag set fixed by the tagset, and the stem
# rule is string prefixing over data already in the DB.
# See latin/LATIN_GLOSS_PLAN.md §5.3.
# --------------------------------------------------------------------------- #

# Universal POS tag -> Whitaker's definition marker.
UPOS_TO_WHITAKER_MARKER = {
    "NOUN": "(n.)", "PROPN": "(n.)",
    "VERB": "(v.)", "AUX": "(v.)",
    "ADJ": "(adj.)",
    "ADV": "(adv.)",
    "PRON": "(pron.)",
    # Latin has no determiner class. The treebank tags possessives and
    # demonstratives DET, and Whitaker files them as ADJECTIVES -- `meus`,
    # `tuus`, `suus`, `vester`, `ullus`, `talis` all carry "(adj.)". Mapping
    # DET to "(pron.)" alone therefore matched nothing for every one of them,
    # so the lookup fell back to whatever else owned the surface: `suo` to the
    # verb "sew together/up", `meo` to "go along, pass, travel", `tuo` to
    # "see, look at". Measured: 158 surfaces / 30,686 tokens, of which the
    # possessive families are ~18,000.
    #
    # Both markers are accepted, pronoun first, so a genuine "(pron.)" entry
    # still wins where one exists.
    "DET": ("(pron.)", "(adj.)"),
    "ADP": "(prep.)",
    "CCONJ": "(conj.)", "SCONJ": "(conj.)",
    "NUM": "(num.)",
    "INTJ": "(interj.)",
}


def select_entry_for_pos(entries: List[DictionaryEntry],
                         upos: Optional[str],
                         lemma: Optional[str]) -> Optional[DictionaryEntry]:
    """Pick the entry that matches the token's POS, tie-broken by its lemma.

    Returns None when the caller should keep its existing behaviour: no
    entries, no usable POS, or no candidate carrying that POS. Never widens the
    candidate set — it can only choose differently within what was already
    returned, so a token with one candidate is untouched.
    """
    if not entries:
        return None
    marker = UPOS_TO_WHITAKER_MARKER.get((upos or "").upper())
    if not marker:
        return None
    markers = (marker,) if isinstance(marker, str) else marker

    # Markers are tried in order, so the first that yields candidates wins and
    # a POS with one marker behaves exactly as before.
    matching = []
    for mk in markers:
        matching = [e for e in entries
                    if (e.definition or "").lstrip().startswith(mk)]
        if matching:
            break
    if not matching:
        return None

    # (1) FORCED — exactly one candidate carries this POS. No judgement is
    # involved, so this cannot pick wrongly between alternatives.
    if len(matching) == 1:
        return matching[0]

    # (2) One stem, several senses of the SAME word. Choosing between senses of
    # one word is low-risk; choosing between different words is not.
    stems = {(e.lemma or "").lower() for e in matching}
    if len(stems) == 1:
        return matching[0]

    # (3) Several DIFFERENT words share this POS. Only the lemma can separate
    # them, and only if it separates them UNAMBIGUOUSLY.
    if lemma:
        low = lemma.lower()
        prefixed = [e for e in matching
                    if e.lemma and low.startswith(e.lemma.lower())]
        if prefixed:
            best = max(len(e.lemma) for e in prefixed)
            longest = [e for e in prefixed if len(e.lemma) == best]
            # Exactly one stem at the longest prefix -> unambiguous.
            if len({(e.lemma or "").lower() for e in longest}) == 1:
                return longest[0]

    # (4) Genuinely ambiguous: several different words, same POS, and the lemma
    # does not separate them. DECLINE rather than guess.
    #
    # An earlier version returned matching[0] here. Measured on Vergil, that
    # arbitrary pick is where the regressions came from — `socios`
    # "companion" -> "sharing", `fatus` "utterance" -> "foolish, silly" — because
    # socius/socio and fatus/fatuus are the same POS and Stanza's lemma does not
    # disambiguate them. Declining keeps the existing gloss, which is no worse
    # than today and often right.
    return None

    # Several same-POS candidates from different stems. Prefer the stem that is
    # the longest prefix of the pipeline's lemma: for lemma "altus" that picks
    # stem "alt" (altus) over "al" (ala); for "casus" it picks "cas" over "cad".
    #
    # Only trust the lemma if it is attested as a headword somewhere — the
    # Stanza path emits fabricated forms ("Troias", "Laviniaqus") that would
    # mislead the prefix test. Attestation is a data lookup, not a list.
    if lemma:
        low = lemma.lower()
        prefixed = [e for e in matching
                    if e.lemma and low.startswith(e.lemma.lower())]
        if prefixed:
            best = max(len(e.lemma) for e in prefixed)
            longest = [e for e in prefixed if len(e.lemma) == best]
            return longest[0]

    return matching[0]


# Longest gloss that still fits under a word in the interlinear.
MAX_GLOSS_CHARS = 50
_ELLIPSIS = "..."

# Whitaker separates senses with any of these.
SENSE_SEPARATORS = ";,/"
_BRACKETS = {"(": ")", "[": "]", "{": "}"}


def _bracket_depth(text):
    """Yield (index, char, depth) with depth counting unclosed brackets."""
    depth = 0
    for i, ch in enumerate(text):
        if ch in _BRACKETS:
            depth += 1
        elif ch in _BRACKETS.values():
            depth = max(0, depth - 1)
            yield i, ch, depth
            continue
        yield i, ch, depth


def first_sense(text, separators=SENSE_SEPARATORS):
    """Text up to the first sense separator that is not inside brackets.

    Whitaker packs examples into brackets and separates them with the same
    punctuation he uses between senses:

        night [prima nocte => early in the night; multa nocte => late at night]
        rise (sun/river)

    Cutting on the first ';' or '/' regardless of depth turns those into
    "night [prima nocte : early in the night" and "rise (sun" - an
    unterminated quotation shown to the reader as a definition.

    A short result is fine. "beg" for "beg, ask for, pray" is terse but correct.
    """
    if not text:
        return text
    for i, ch, depth in _bracket_depth(text):
        if ch in separators and depth == 0:
            return text[:i].strip()
    return text.strip()


def balance_brackets(text):
    """Repair brackets left unmatched, in either direction.

    Two ways a gloss ends up unbalanced:

    - An *unclosed* opener, when the length cap lands inside brackets because
      one sense exceeds the cap on its own. Cutting back to the opener gives
      what a reader wants: "praetor (official elected by the Romans who
      serv..." becomes "praetor".
    - An *unmatched closer*, from malformed source. Whitaker has entries like
      "(n.) small pot for cooking/preserving);" where stripping the leading
      part-of-speech marker leaves an orphan ")". Those are simply removed.

    Brackets are counted by depth, not matched by type, so a source typo that
    opens with "[" and closes with ")" is left alone. That is deliberate: the
    depth counter is the behaviour first_sense() is verified against, and one
    L&S article in 96,378 is not worth risking a change to the other 96,377.
    """
    if not text:
        return text
    opens, orphan_closers = [], []
    for i, ch, _ in _bracket_depth(text):
        if ch in _BRACKETS:
            opens.append(i)
        elif ch in _BRACKETS.values():
            if opens:
                opens.pop()
            else:
                orphan_closers.append(i)
    if not opens and not orphan_closers:
        return text
    cut = opens[0] if opens else len(text)
    kept = "".join(c for i, c in enumerate(text[:cut])
                   if i not in set(orphan_closers))
    trimmed = kept.strip().rstrip(",;:.-")
    if len(trimmed) >= 2:
        return trimmed
    # Trimming leaves nothing usable, so keep the words and drop the brackets
    # rather than losing the gloss entirely.
    return "".join(c for c in text if c not in _BRACKETS
                   and c not in _BRACKETS.values()).strip()


def extract_gloss(entry: DictionaryEntry) -> str:
    """
    Extract a simple English gloss from a Latin dictionary entry.

    Whitaker's format is cleaner than LSJ - definitions are already English
    with part of speech markers like "(n.)", "(v.)", "(adj.)", etc.

    Preserves enclitic suffixes like "+ -que (and)" at the end.
    """
    if not entry or not entry.definition:
        return "???"

    text = entry.definition.strip()

    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)

    # Remove part of speech markers at start
    text = re.sub(r'^\([^)]+\)\s*', '', text)

    # Check for enclitic suffix (e.g., "+ -que (and)", "+ -ve (or)", "+ -ne (?)")
    # These appear at the end of definitions for words with enclitics stripped
    enclitic_suffix = ""
    enclitic_match = re.search(r'\s*\+\s*-(\w+)\s*\(([^)]+)\)\s*$', text)
    if enclitic_match:
        # Extract the enclitic meaning (e.g., "and", "or", "?")
        enclitic_meaning = enclitic_match.group(2)
        enclitic_suffix = f" + {enclitic_meaning}"
        # Remove the enclitic from text for processing
        text = text[:enclitic_match.start()].strip()

    # First sense only; commas are a sense boundary only when still too long.
    text = first_sense(text, ";")
    if len(text) > MAX_GLOSS_CHARS:
        text = first_sense(text, ",")

    # Remove trailing punctuation
    text = text.rstrip('.,;:')

    # Re-append enclitic suffix
    text = text + enclitic_suffix

    # Truncate if still too long
    if len(text) > MAX_GLOSS_CHARS:
        text = text[:MAX_GLOSS_CHARS - len(_ELLIPSIS)] + _ELLIPSIS

    # Any cut above may have opened a bracket it never closes.
    text = balance_brackets(text)

    # Return "???" if empty
    if not text or len(text) < 2:
        return "???"

    return text


if __name__ == "__main__":
    # Test the module standalone
    import sys

    if len(sys.argv) < 2:
        print("Usage: python latin_dictionary_lookup.py <database_path> [word]")
        sys.exit(1)

    db_path = sys.argv[1]
    repo = LatinRepository(db_path)

    if len(sys.argv) >= 3:
        word = sys.argv[2]
        entries = repo.get_all_dictionary_entries(word, "latin")
        print(f"\nLookup results for '{word}':")
        for entry in entries:
            gloss = extract_gloss(entry)
            print(f"  Lemma: {entry.lemma}")
            print(f"  Definition: {entry.definition[:100]}...")
            print(f"  Gloss: {gloss}")
            print(f"  Source: {entry.source}")
            print()
    else:
        # Test some common words
        test_words = ['arma', 'virum', 'cano', 'Troiae', 'qui', 'primus', 'ab', 'oris']
        for word in test_words:
            entries = repo.get_all_dictionary_entries(word, "latin")
            if entries:
                gloss = extract_gloss(entries[0])
                print(f"{word}: {gloss} ({entries[0].source})")
            else:
                print(f"{word}: ???")
