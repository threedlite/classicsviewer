#!/usr/bin/env python3
"""
verify_module_output.py — table-by-table DB verification for the Greek/Latin
module extraction (Phase 0 of GREEK_LATIN_MODULE_ANALYSIS.md).

Two modes:

  snapshot <db> <manifest.json> [--language LANG]
    Write a per-table manifest (row count + streaming content hash) for the
    given database. Filter to a single language if --language is given.

  compare <db_a> <db_b> [--language LANG]
    Compare two databases table-by-table directly (no manifest file).

  verify <db> <manifest.json> [--language LANG]
    Verify a database against a previously-captured manifest.

Content hashing skips the auto-incrementing integer `id` column where it is
purely a surrogate key, so that a merged database whose IDs have been
renumbered by merge_database.py still matches its source.

Row ordering for hashing is explicit per table — SQLite has no guaranteed
row order without ORDER BY.
"""

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Table configuration
# ---------------------------------------------------------------------------
#
# Each entry is a dict with:
#   hash_cols : columns included in the content hash (excludes renumbering
#               integer PKs so merged DBs stay equivalent)
#   order_by  : SQL ORDER BY clause (must be deterministic)
#   lang_sql  : optional {language: WHERE clause} map. A table with no entry
#               for a given language is skipped when filtering to that
#               language. For joined tables the SQL may include join
#               subqueries against authors/works/books.
#
# Per-language source filters for lemma_map / dictionary_entries were
# identified by scanning current module DBs:
#   - latin/latin_texts.db: source = 'Whitaker'
#   - greek/greek_texts.db: lsj, cunliffe, wiktionary, Enhanced Wiktionary,
#     perseus_treebank, inflection_of, generated, wiktionary:grc-conj,
#     wiktionary:grc-decl

LANG_SOURCES_LEMMA_MAP = {
    "latin": ("Whitaker", "Whitaker UNIQUES"),
    "greek": ("lsj", "cunliffe", "wiktionary", "Enhanced Wiktionary",
              "perseus_treebank", "inflection_of", "generated",
              "wiktionary:grc-conj", "wiktionary:grc-decl"),
}


def _simple_lang_sql(lang: str, col: str = "language") -> str:
    return f"{col} = '{lang}'"


def _join_authors(lang: str, ref_col: str) -> str:
    return (f"{ref_col} IN (SELECT id FROM authors "
            f"WHERE language='{lang}')")


def _join_works(lang: str, ref_col: str) -> str:
    return (f"{ref_col} IN (SELECT w.id FROM works w "
            f"JOIN authors a ON w.author_id=a.id "
            f"WHERE a.language='{lang}')")


def _join_books(lang: str, ref_col: str) -> str:
    return (f"{ref_col} IN (SELECT b.id FROM books b "
            f"JOIN works w ON b.work_id=w.id "
            f"JOIN authors a ON w.author_id=a.id "
            f"WHERE a.language='{lang}')")


def _lemma_map_sql(lang: str) -> str:
    sources = LANG_SOURCES_LEMMA_MAP[lang]
    if len(sources) == 1:
        return f"source = '{sources[0]}'"
    return "source IN (" + ",".join(f"'{s}'" for s in sources) + ")"


def _build_lang_sql(lang: str, kind: str, **kwargs) -> str:
    """Generate language-filter SQL for a given table kind."""
    if kind == "language_col":
        return _simple_lang_sql(lang, kwargs.get("col", "language"))
    if kind == "author_ref":
        return _join_authors(lang, kwargs["col"])
    if kind == "work_ref":
        return _join_works(lang, kwargs["col"])
    if kind == "book_ref":
        return _join_books(lang, kwargs["col"])
    if kind == "lemma_map":
        return _lemma_map_sql(lang)
    raise ValueError(f"unknown kind: {kind}")


TABLES: Dict[str, dict] = {
    "authors": {
        "hash_cols": ["id", "name", "name_alt", "language", "has_translations"],
        "order_by": "id",
        "lang_sql_kind": ("language_col", {}),
    },
    "works": {
        "hash_cols": ["id", "author_id", "title", "title_alt", "title_english",
                      "type", "urn", "description"],
        "order_by": "id",
        "lang_sql_kind": ("author_ref", {"col": "author_id"}),
    },
    "books": {
        "hash_cols": ["id", "work_id", "book_number", "label",
                      "start_line", "end_line", "line_count"],
        "order_by": "id",
        "lang_sql_kind": ("work_ref", {"col": "work_id"}),
    },
    "text_lines": {
        # id is AUTOINCREMENT; omit from hash so merged DB matches.
        "hash_cols": ["book_id", "line_number", "sequence_number",
                      "line_text", "line_xml", "speaker"],
        "order_by": "book_id, sequence_number, line_number",
        "lang_sql_kind": ("book_ref", {"col": "book_id"}),
    },
    "words": {
        "hash_cols": ["word", "book_id", "line_number", "sequence_number", "word_position"],
        "order_by": "book_id, line_number, sequence_number, word_position",
        "lang_sql_kind": ("book_ref", {"col": "book_id"}),
    },
    "translation_segments": {
        "hash_cols": ["book_id", "start_line", "end_line", "sequence_number",
                      "translation_text", "translator", "speaker"],
        "order_by": "book_id, sequence_number, start_line",
        "lang_sql_kind": ("book_ref", {"col": "book_id"}),
    },
    "translation_lookup": {
        # segment_id references translation_segments.id (renumbers on merge);
        # join to its semantic key so the hash is merge-stable.
        "hash_cols_sql": """
            tl.book_id, tl.line_number,
            ts.book_id AS seg_book_id, ts.start_line AS seg_start,
            ts.end_line AS seg_end, ts.sequence_number AS seg_seq
        """,
        "from_sql": "translation_lookup tl JOIN translation_segments ts ON tl.segment_id = ts.id",
        "order_by": "tl.book_id, tl.line_number, ts.sequence_number, ts.start_line",
        "lang_sql_kind": ("book_ref", {"col": "tl.book_id"}),
    },
    "dictionary_entries": {
        # id is AUTOINCREMENT; omit.
        # Exclude the single database_build_metadata row — its entry_plain
        # contains a build timestamp that changes every build.
        "hash_cols": ["headword", "headword_normalized_ultra", "language",
                      "entry_xml", "entry_html", "entry_plain", "source"],
        "order_by": "language, source, headword, entry_plain",
        "always_where": "source != 'database_build_metadata'",
        "lang_sql_kind": ("language_col", {}),
    },
    "lemma_map": {
        # id is AUTOINCREMENT; omit. ORDER BY includes every hash column so
        # that tied rows (same keys but different normalized form / confidence)
        # can't flip hash between builds.
        "hash_cols": ["word_form", "word_form_normalized_ultra", "lemma",
                      "confidence", "source", "morph_info"],
        "order_by": "source, word_form, lemma, morph_info, word_form_normalized_ultra, confidence",
        "lang_sql_kind": ("lemma_map", {}),
    },
    "milestone_line_ranges": {
        "hash_cols": ["work_id", "milestone", "start_line", "end_line"],
        "order_by": "work_id, milestone",
        "lang_sql_kind": ("work_ref", {"col": "work_id"}),
    },
    "normalization_patterns": {
        "hash_cols": ["language", "pattern", "replacement", "description", "priority"],
        "order_by": "language, priority, pattern",
        "lang_sql_kind": ("language_col", {}),
    },
    "prefix_assimilation_rules": {
        "hash_cols": ["language", "base_prefix", "assimilated_form", "meaning",
                      "phonological_rule", "priority", "examples"],
        "order_by": "language, priority, base_prefix, assimilated_form",
        "lang_sql_kind": ("language_col", {}),
    },
}


SUPPORTED_LANGUAGES = ("latin", "greek")

BATCH = 5000


def canonicalize(row: tuple) -> bytes:
    """Deterministic byte representation of a row for hashing."""
    return json.dumps(row, ensure_ascii=False, default=str,
                      separators=(",", ":"), sort_keys=False).encode("utf-8")


def hash_table(conn: sqlite3.Connection, table: str, cfg: dict,
               language: Optional[str]) -> Tuple[int, str]:
    """Return (row_count, md5_hex) for a table under the given filter."""
    if "hash_cols_sql" in cfg:
        cols_sql = cfg["hash_cols_sql"]
        from_sql = cfg["from_sql"]
    else:
        cols_sql = ", ".join(cfg["hash_cols"])
        from_sql = table

    clauses = []
    always_where = cfg.get("always_where")
    if always_where:
        clauses.append(always_where)
    if language is not None:
        lang_kind = cfg.get("lang_sql_kind")
        if lang_kind is None:
            return (-1, "SKIP")
        kind, kwargs = lang_kind
        clauses.append(_build_lang_sql(language, kind, **kwargs))
    where = (" WHERE " + " AND ".join(f"({c})" for c in clauses)) if clauses else ""

    count_sql = f"SELECT COUNT(*) FROM {from_sql}{where}"
    (n,) = conn.execute(count_sql).fetchone()

    hasher = hashlib.md5()
    if n == 0:
        return (0, hasher.hexdigest())

    query = f"SELECT {cols_sql} FROM {from_sql}{where} ORDER BY {cfg['order_by']}"
    cur = conn.execute(query)
    while True:
        rows = cur.fetchmany(BATCH)
        if not rows:
            break
        for row in rows:
            hasher.update(canonicalize(row))
            hasher.update(b"\n")
    return (n, hasher.hexdigest())


def build_manifest(db_path: str, language: Optional[str],
                   verbose: bool = True) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA query_only = 1")
    manifest = {
        "db": str(Path(db_path).resolve()),
        "language": language,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tables": {},
    }
    for table, cfg in TABLES.items():
        t0 = time.time()
        n, h = hash_table(conn, table, cfg, language)
        dt = time.time() - t0
        manifest["tables"][table] = {"count": n, "hash": h}
        if verbose:
            mark = "—" if h == "SKIP" else ("·" if n == 0 else "✓")
            print(f"  {mark} {table:30s} rows={n:>12,}  hash={h[:12]}  ({dt:>5.1f}s)")
    conn.close()
    return manifest


def load_manifest(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_manifest(manifest: dict, path: str):
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)


def diff_manifests(a: dict, b: dict) -> int:
    """Return number of differing tables."""
    tables = set(a["tables"]) | set(b["tables"])
    diffs = 0
    for t in sorted(tables):
        ra = a["tables"].get(t, {"count": None, "hash": None})
        rb = b["tables"].get(t, {"count": None, "hash": None})
        if ra == rb:
            print(f"  ✓ {t:30s} rows={ra['count']:>12,}  hash={ra['hash'][:12]}")
        else:
            diffs += 1
            print(f"  ✗ {t:30s}")
            print(f"      A: rows={ra['count']} hash={ra['hash']}")
            print(f"      B: rows={rb['count']} hash={rb['hash']}")
    return diffs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("snapshot", help="write manifest for a DB")
    s.add_argument("db")
    s.add_argument("manifest")
    s.add_argument("--language", choices=list(SUPPORTED_LANGUAGES), default=None)

    c = sub.add_parser("compare", help="compare two DBs directly")
    c.add_argument("db_a")
    c.add_argument("db_b")
    c.add_argument("--language", choices=list(SUPPORTED_LANGUAGES), default=None)

    v = sub.add_parser("verify", help="compare DB to manifest")
    v.add_argument("db")
    v.add_argument("manifest")
    v.add_argument("--language", choices=list(SUPPORTED_LANGUAGES), default=None)

    args = ap.parse_args(argv)

    if args.cmd == "snapshot":
        print(f"Snapshotting {args.db} (language={args.language or 'all'})")
        m = build_manifest(args.db, args.language)
        save_manifest(m, args.manifest)
        print(f"Manifest written to {args.manifest}")
        return 0

    if args.cmd == "compare":
        print(f"A: {args.db_a}")
        print(f"B: {args.db_b}")
        print(f"Language filter: {args.language or 'all'}")
        print("\nHashing A...")
        ma = build_manifest(args.db_a, args.language)
        print("\nHashing B...")
        mb = build_manifest(args.db_b, args.language)
        print("\n=== DIFF ===")
        diffs = diff_manifests(ma, mb)
        print(f"\n{diffs} table(s) differ." if diffs else "\nAll tables match.")
        return 1 if diffs else 0

    if args.cmd == "verify":
        manifest = load_manifest(args.manifest)
        if manifest.get("language") != args.language:
            print(f"WARNING: manifest language={manifest.get('language')!r}, "
                  f"but --language={args.language!r}", file=sys.stderr)
        print(f"Hashing {args.db}...")
        cur = build_manifest(args.db, args.language)
        print("\n=== VERIFY ===")
        diffs = diff_manifests(manifest, cur)
        print(f"\n{diffs} table(s) differ." if diffs else "\nAll tables match manifest.")
        return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
