"""Pack layout registry for the Android extended delta.

Design: ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md (revised 2026-09-27).

Everything the assembly needs to (a) cut the full DB out of the extended DB
by filtering, ids preserved, and (b) cut the extended delta into on-demand
asset packs, lives here so the Python and the Gradle/Kotlin sides read one
definition. Nothing in this file touches data; it only names sets and
constants.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# Google Play budget. 1.5 GB per pack is published and applies to everyone.
# The cumulative on-demand figure was probed on 2026-09-27: a 10.26 GB
# on-demand bundle was accepted on the internal track and passed the
# production review screen. The build plans against the probed figure, not
# the published 30 GB.
# ---------------------------------------------------------------------------
PLAY_PER_PACK_CAP_BYTES = 1_500_000_000
PLAY_ON_DEMAND_BUDGET_BYTES = 10_000_000_000
PART_SIZE_TARGET_BYTES = 1_200_000_000  # decided: 20 percent under the cap

# Ids must stay below 2^31: three Room entity fields are declared Int.
MAX_ID_EXCLUSIVE = 2 ** 31

# ---------------------------------------------------------------------------
# What the full DB is, as a rule over the extended DB (verified 2026-09-27:
# the rule reproduces today's full DB exactly, apart from the build_time row
# and two derived has_translations flags).
#
#   Greek:   works whose id carries neither the First1K nor the PTA suffix.
#   Others:  every work of every language in FULL_TEXT_LANGUAGES.
#   Lexicon: every row of every language in FULL_LEXICON_LANGUAGES.
#
# Language names are compared lower-cased; authors.language and
# dictionary_entries.language are lower-case in the data, while the merge
# descriptions in assemble_database.py are mixed-case ("Greek", "old_english").
# ---------------------------------------------------------------------------
GREEK_DELTA_SUFFIXES: Tuple[str, ...] = ("_OGL", "_PTA")
FULL_TEXT_LANGUAGES: FrozenSet[str] = frozenset(
    {"latin", "italian", "old_english", "sumerian", "akkadian"}
)
FULL_LEXICON_LANGUAGES: FrozenSet[str] = frozenset(
    {"greek", "latin", "sumerian", "akkadian", "old_english"}
)

# Every language the extended DB carries, for the delta's unit list.
EXTENDED_LANGUAGES: FrozenSet[str] = FULL_TEXT_LANGUAGES | frozenset(
    {"greek", "sanskrit", "pali", "coptic", "hebrew", "syriac", "norse",
     "chinese", "persian", "arabic"}
)

LEXICON_TABLES: Tuple[str, ...] = (
    "dictionary_entries",
    "lemma_map",
    "normalization_patterns",
    "prefix_assimilation_rules",
)
TEXT_TABLES_BY_BOOK: Tuple[str, ...] = (
    "text_lines",
    "translation_segments",
    "words",
    "translation_lookup",
)
AUTOINCREMENT_TABLES: Tuple[str, ...] = (
    "text_lines",
    "translation_segments",
    "words",
    "dictionary_entries",
    "lemma_map",
    "normalization_patterns",
    "prefix_assimilation_rules",
)

# ---------------------------------------------------------------------------
# lemma_map has no language column. Rows are attributed to a language by the
# id ranges the assembly records at each insertion stage; this map is the
# cross-check: every row inside a language's ranges must carry a source
# registered to that language, and every source in the DB must be
# registered. An unknown source fails the extended build, which is the
# intended way a new lexicon source announces itself.
#
# Measured from the 2026-09-14 extended DB (section 3 of the proposal).
# ---------------------------------------------------------------------------
SOURCE_LANGUAGE: Dict[str, str] = {
    # greek
    "oga": "greek",
    "wiktionary": "greek",
    "wiktionary:grc-decl": "greek",
    "wiktionary:grc-conj": "greek",
    "perseus_treebank": "greek",
    "Enhanced Wiktionary": "greek",
    "lsj": "greek",
    "inflection_of": "greek",
    "cunliffe": "greek",
    "generated": "greek",
    # latin
    "Lewis & Short glosses": "latin",
    "Whitaker": "latin",
    "Perseus LDT": "latin",
    # sumerian / akkadian / old english
    "ePSD2": "sumerian",
    "RINAP": "akkadian",
    "Bosworth-Toller": "old_english",
    # extended-only languages
    "DCS": "sanskrit",
    "DCS+Sandhi": "sanskrit",
    "OSHB morphhb": "hebrew",
    "IcePaHC": "norse",
    "Zoega": "norse",
    "Thorpe Glossary": "norse",
    "coptic_scriptorium": "coptic",
    "comprehensive_coptic_lexicon": "coptic",
    "Statistical Dictionary": "pali",
}

# The build-time marker row the assembly writes; it is the release identity.
BUILD_TIME_ROW = {"language": "system", "headword": "build_time"}

# The rule the Greek module (monolith_fn.py, "Updating has_translations
# flag") and the Latin module (create_latin_database.py, "UPDATING
# has_translations FLAG") apply, verbatim. The filter recomputes the flag
# for the rows it keeps with the same statement.
HAS_TRANSLATIONS_UPDATE_SQL = """
        UPDATE authors
        SET has_translations = 1
        WHERE id IN (
            SELECT DISTINCT a.id
            FROM authors a
            JOIN works w ON a.id = w.author_id
            JOIN books b ON w.id = b.work_id
            JOIN translation_segments ts ON b.id = ts.book_id
            WHERE ts.translation_text IS NOT NULL
            AND LENGTH(TRIM(ts.translation_text)) > 10
            AND (ts.translator IS NULL OR ts.translator NOT LIKE '%Interlinear%')
        )
"""


def normalize_language(name: str) -> str:
    """Language names as the data spells them: lower-case, trimmed."""
    return name.strip().lower()


def full_works_where_sql(works_alias: str = "w", authors_alias: str = "a") -> str:
    """SQL predicate selecting the full DB's works from a works/authors join.

    The caller supplies `FROM works w JOIN authors a ON a.id = w.author_id`
    (with whatever schema prefix it needs); this returns the WHERE body.
    """
    w, a = works_alias, authors_alias
    suffix_clauses = " AND ".join(
        f"{w}.id NOT LIKE '%\\{s}' ESCAPE '\\'" for s in GREEK_DELTA_SUFFIXES
    )
    langs = ", ".join(f"'{lang}'" for lang in sorted(FULL_TEXT_LANGUAGES))
    return (
        f"(({a}.language = 'greek' AND {suffix_clauses}) "
        f"OR {a}.language IN ({langs}))"
    )
