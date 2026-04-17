"""Canonical Perseus database schema — single source of truth.

The DDL strings below are extracted verbatim from the shipped
`perseus_texts-2.db` (Apr 2026 release). They are reproduced byte-for-byte
because SQLite stores CREATE statement text in `sqlite_master.sql`, and
Android Room validates schemas on every app launch — any drift from the
shipped DDL crashes existing installations on upgrade.

DO NOT MODIFY any DDL string here without a migration plan. Column
renames, added NOT NULLs, dropped indexes, and even whitespace-normalized
rewrites risk silent breakage.

Callers:
  - data-prep/create_perseus_database.py      (monolith)
  - data-prep/build_modules/load_combined_dictionaries.py
  - latin/create_latin_database.py

Future callers (once Phase 2 lands):
  - greek/create_greek_database.py
  - data-prep/assemble_database.py
"""

import sqlite3
from typing import List


# ---------------------------------------------------------------------------
# Tables — in FK-safe creation order. Parent tables first.
# ---------------------------------------------------------------------------

TABLE_DDL: List[str] = [
    """CREATE TABLE authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        )""",
    """CREATE TABLE works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_alt TEXT,
            title_english TEXT,
            type TEXT,
            urn TEXT,
            description TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )""",
    """CREATE TABLE books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER NOT NULL,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        )""",
    """CREATE TABLE text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )""",
    """CREATE TABLE translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            sequence_number INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )""",
    """CREATE TABLE milestone_line_ranges (
            work_id TEXT,
            milestone TEXT,
            start_line INTEGER,
            end_line INTEGER,
            PRIMARY KEY (work_id, milestone)
        )""",
    """CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )""",
    """CREATE TABLE dictionary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            headword TEXT NOT NULL,
            headword_normalized_ultra TEXT,
            language TEXT NOT NULL,
            entry_xml TEXT,
            entry_html TEXT,
            entry_plain TEXT,
            source TEXT
        )""",
    """CREATE TABLE lemma_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT,
            morph_info TEXT
        )""",
    """CREATE TABLE normalization_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            pattern TEXT NOT NULL,
            replacement TEXT NOT NULL,
            description TEXT,
            priority INTEGER NOT NULL
        )""",
    """CREATE TABLE prefix_assimilation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            language TEXT NOT NULL,
            base_prefix TEXT NOT NULL,
            assimilated_form TEXT NOT NULL,
            meaning TEXT,
            phonological_rule TEXT,
            priority INTEGER NOT NULL,
            examples TEXT
        )""",
    """CREATE TABLE translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        )""",
]


# ---------------------------------------------------------------------------
# Indexes — grouped by table, text preserves the shipped `sqlite_master.sql`
# exactly (including the trailing-space quirks on some lines). Do not reflow.
# ---------------------------------------------------------------------------

INDEX_DDL: List[str] = [
    """CREATE INDEX idx_authors_language
        ON authors(language)""",
    """CREATE INDEX idx_works_author
        ON works(author_id)""",
    """CREATE INDEX idx_books_work
        ON books(work_id)""",
    """CREATE INDEX idx_text_lines_book
        ON text_lines(book_id)""",
    """CREATE INDEX idx_text_lines_sequence
        ON text_lines(book_id, sequence_number)""",
    """CREATE INDEX idx_translation_segments_book
        ON translation_segments(book_id)""",
    """CREATE INDEX idx_translation_segments_lines
        ON translation_segments(book_id, start_line)""",
    """CREATE INDEX idx_words_word
        ON words(word)""",
    """CREATE INDEX idx_words_book_line_seq
        ON words(book_id, line_number, sequence_number)""",
    """CREATE INDEX idx_dictionary_headword
        ON dictionary_entries(headword, language)""",
    """CREATE INDEX idx_dictionary_headword_ultra
        ON dictionary_entries(headword_normalized_ultra, language)""",
    """CREATE INDEX idx_lemma_map_word
        ON lemma_map(word_form)""",
    """CREATE INDEX idx_lemma_map_word_ultra
        ON lemma_map(word_form_normalized_ultra)""",
    """CREATE INDEX idx_lemma_map_lemma
        ON lemma_map(lemma)""",
    """CREATE INDEX idx_normalization_language
        ON normalization_patterns(language, priority)""",
    """CREATE INDEX idx_prefix_assimilation_language
        ON prefix_assimilation_rules(language)""",
    """CREATE INDEX idx_prefix_assimilation_base
        ON prefix_assimilation_rules(base_prefix)""",
    """CREATE INDEX idx_prefix_assimilation_form
        ON prefix_assimilation_rules(assimilated_form)""",
    """CREATE INDEX idx_prefix_assimilation_lang_priority
        ON prefix_assimilation_rules(language, priority)""",
    "CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number)",
    "CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id)",
]


SCHEMA_DDL: List[str] = TABLE_DDL + INDEX_DDL


def _table_names() -> List[str]:
    """Extract table names from TABLE_DDL in declared (FK-safe) order."""
    import re
    names = []
    for ddl in TABLE_DDL:
        m = re.search(r"CREATE TABLE\s+(\w+)", ddl)
        if not m:
            raise RuntimeError(f"Could not parse table name from: {ddl[:60]!r}")
        names.append(m.group(1))
    return names


def create_schema(conn: sqlite3.Connection, reset: bool = True) -> None:
    """Apply the canonical schema to `conn`. Commits.

    With `reset=True` (default), DROP TABLE IF EXISTS is issued for every
    canonical table first (in reverse FK order) so the call is idempotent
    against a DB carrying prior-build state. This matches the monolith's
    historical DROP+CREATE pattern and is safe on a fresh DB.

    With `reset=False`, assumes all canonical tables are absent; errors on
    conflict. Useful for assembly/merge flows where the caller has already
    guaranteed an empty DB.
    """
    cur = conn.cursor()
    if reset:
        for name in reversed(_table_names()):
            cur.execute(f"DROP TABLE IF EXISTS {name}")
    for ddl in SCHEMA_DDL:
        cur.execute(ddl)
    conn.commit()


# ---------------------------------------------------------------------------
# Drift detection — used by verify_module_output.py and by build scripts
# that want to assert their output matches the shipped schema.
# ---------------------------------------------------------------------------

def expected_sqlite_master() -> dict:
    """Return {name: sql} for every table and index in the canonical schema.

    Mirrors what `SELECT name, sql FROM sqlite_master` returns after
    create_schema() runs on an empty DB. Built by actually running the DDL
    so that any whitespace SQLite normalizes shows up here the same way it
    will in a built DB — avoiding false diffs.
    """
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    result = {name: sql for name, sql in cur.fetchall()}
    conn.close()
    return result


def _normalize_ddl(sql: str) -> str:
    """Collapse whitespace so two DDL strings compare on semantics only.

    SQLite preserves CREATE-statement text verbatim in `sqlite_master.sql`,
    including the incidental whitespace of whoever wrote the Python string.
    The shipped monolith has trailing spaces after index names and trailing
    `\\n    ` before the closing `)` on many statements. Room validates the
    parsed schema, not the text, so this whitespace is cosmetic. Collapse it
    before comparing so the check focuses on real drift.
    """
    import re
    return re.sub(r"\s+", " ", sql).strip()


def diff_against_canonical(conn: sqlite3.Connection) -> List[str]:
    """Return human-readable diffs between `conn`'s schema and canonical.

    Empty list = schemas match. Each returned string describes one mismatch
    (missing table/index, extra table/index, or normalized-DDL mismatch).
    """
    expected = expected_sqlite_master()
    cur = conn.cursor()
    cur.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
    )
    actual = {name: sql for name, sql in cur.fetchall()}

    diffs = []
    for name in sorted(set(expected) | set(actual)):
        if name not in actual:
            diffs.append(f"missing: {name}")
        elif name not in expected:
            diffs.append(f"extra:   {name}")
        elif _normalize_ddl(expected[name]) != _normalize_ddl(actual[name]):
            diffs.append(
                f"drift:   {name}\n"
                f"  expected: {_normalize_ddl(expected[name])!r}\n"
                f"  actual:   {_normalize_ddl(actual[name])!r}"
            )
    return diffs


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "--check-self":
        # Apply to a fresh in-memory DB and confirm round-trip matches.
        conn = sqlite3.connect(":memory:")
        create_schema(conn)
        diffs = diff_against_canonical(conn)
        if diffs:
            print("FAIL: canonical schema drifted from itself:")
            for d in diffs:
                print(f"  {d}")
            sys.exit(1)
        print(f"OK: {len(TABLE_DDL)} tables + {len(INDEX_DDL)} indexes applied cleanly")
        sys.exit(0)

    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        db_path = sys.argv[2]
        conn = sqlite3.connect(db_path)
        diffs = diff_against_canonical(conn)
        if diffs:
            print(f"FAIL: {db_path} differs from canonical schema:")
            for d in diffs:
                print(f"  {d}")
            sys.exit(1)
        print(f"OK: {db_path} matches canonical schema")
        sys.exit(0)

    print(
        "usage:\n"
        "  python -m shared.database_schema --check-self\n"
        "  python -m shared.database_schema --check <path-to-db>"
    )
    sys.exit(2)
