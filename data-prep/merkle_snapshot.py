#!/usr/bin/env python3
"""
merkle_snapshot.py — build hashed snapshots of a Classics Viewer DB and diff them.

Stores every row's hash in a SQLite snapshot DB so that diffs work even on the
~49 M-word extended database.

Usage:
  python3 merkle_snapshot.py snapshot <db_path> <snapshot_path>
  python3 merkle_snapshot.py diff <before_snapshot> <after_snapshot>

Excludes autoincrement `id` columns (shift between rebuilds) and dereferences
FKs to autoincrement ids into natural-key tuples so the tree hash is stable when
the underlying content is unchanged.

3-tier tree:
    root  ->  per-table  ->  per-book  ->  per-row (SHA-256)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.venv_check import assert_libs  # noqa: E402
assert_libs("merkle")
import json
import sqlite3
import hashlib
import time
from collections import defaultdict

# Tables to snapshot. Each entry:
#   columns_to_hash: tuple of column names included in row hash, in order
#   natural_key: tuple of column names used for sorting & identifying rows
#   book_id_col: column used as the per-book group ('_global_' if no book_id)
#   fk_dereferences: dict of virtual_col -> (referenced_table, sql_to_resolve)
#       Resolver SQL takes ?=fk_value and returns the natural-key columns.
#   _dynamic: if True, discover columns at runtime; sort by all non-id columns.
TABLES = {
    "authors": {
        "columns_to_hash": ("id", "name", "name_alt", "language", "has_translations"),
        "natural_key": ("id",),
        "book_id_col": "_global_",
        "fk_dereferences": {},
    },
    "works": {
        "columns_to_hash": ("id", "author_id", "title", "title_alt", "title_english", "type", "urn", "description"),
        "natural_key": ("id",),
        "book_id_col": "_global_",
        "fk_dereferences": {},
    },
    "books": {
        "columns_to_hash": ("id", "work_id", "book_number", "label", "start_line", "end_line", "line_count"),
        "natural_key": ("id",),
        "book_id_col": "_global_",
        "fk_dereferences": {},
    },
    "text_lines": {
        "columns_to_hash": ("book_id", "line_number", "sequence_number", "line_text", "line_xml", "speaker"),
        "natural_key": ("book_id", "sequence_number"),
        "book_id_col": "book_id",
        "fk_dereferences": {},
    },
    "words": {
        "columns_to_hash": ("book_id", "line_number", "sequence_number", "word_position", "word"),
        "natural_key": ("book_id", "line_number", "sequence_number", "word_position"),
        "book_id_col": "book_id",
        "fk_dereferences": {},
    },
    "translation_segments": {
        "columns_to_hash": ("book_id", "translator", "sequence_number", "start_line", "end_line", "translation_text", "speaker"),
        "natural_key": ("book_id", "translator", "sequence_number"),
        "book_id_col": "book_id",
        "fk_dereferences": {},
    },
    "translation_lookup": {
        # segment_id resolved to (translator, sequence_number) for stability
        "columns_to_hash": ("book_id", "line_number", "_segment_natural"),
        "natural_key": ("book_id", "line_number", "_segment_natural"),
        "book_id_col": "book_id",
        "fk_dereferences": {
            "_segment_natural": (
                "translation_segments",
                "SELECT translator, sequence_number FROM translation_segments WHERE id = ?",
            ),
        },
    },
    "milestone_line_ranges": {"_dynamic": True, "book_id_col": "book_id"},
    "lemma_map": {"_dynamic": True, "book_id_col": "_global_"},
    "dictionary_entries": {"_dynamic": True, "book_id_col": "_global_"},
    "normalization_patterns": {"_dynamic": True, "book_id_col": "_global_"},
    "prefix_assimilation_rules": {"_dynamic": True, "book_id_col": "_global_"},
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS table_hashes (
    table_name TEXT PRIMARY KEY,
    table_hash TEXT NOT NULL,
    natural_key TEXT NOT NULL,
    book_id_col TEXT NOT NULL,
    row_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS book_hashes (
    table_name TEXT NOT NULL,
    book_id TEXT NOT NULL,
    book_hash TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    PRIMARY KEY (table_name, book_id)
);
CREATE TABLE IF NOT EXISTS row_hashes (
    table_name TEXT NOT NULL,
    book_id TEXT NOT NULL,
    natural_key_json TEXT NOT NULL,
    row_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_row_hashes_lookup
    ON row_hashes(table_name, book_id, natural_key_json);
CREATE INDEX IF NOT EXISTS idx_row_hashes_match
    ON row_hashes(table_name, book_id, natural_key_json, row_hash);
CREATE TABLE IF NOT EXISTS skipped (
    table_name TEXT PRIMARY KEY,
    reason TEXT NOT NULL
);
"""


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canon_values(values) -> str:
    # Use Python repr per value separated by US (0x1f) for unambiguous serialization.
    return "\x1f".join(repr(v) for v in values)


def hash_row(values) -> str:
    return sha256(canon_values(values))


def hash_group(row_hashes_sorted) -> str:
    return sha256("\n".join(row_hashes_sorted))


def detect_autoincrement_id(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = cur.fetchall()
    pk_cols = [c for c in cols if c[5] > 0]
    if len(pk_cols) == 1 and pk_cols[0][2].upper() == "INTEGER":
        try:
            row = conn.execute("SELECT 1 FROM sqlite_sequence WHERE name=?", (table,)).fetchone()
            if row:
                return pk_cols[0][1]
        except sqlite3.OperationalError:
            pass
    return None


def get_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [c[1] for c in cur.fetchall()]


def stream_rows_explicit(conn, table, spec):
    """Yield (book_id, natural_key_tuple, columns_to_hash_tuple) for each row in `table`.

    Resolves FKs declared in spec['fk_dereferences'].
    """
    cols = list(spec["columns_to_hash"])
    natural_key = list(spec["natural_key"])
    book_id_col = spec["book_id_col"]
    fk_derefs = spec.get("fk_dereferences", {})

    # Determine which real columns to SELECT.
    # Convention: virtual column "_X_..." derives from real fk column "X_id".
    real_cols = []
    virtual_to_real = {}
    for c in cols:
        if c.startswith("_"):
            base = c.lstrip("_").split("_")[0]
            real_fk = base + "_id"
            virtual_to_real[c] = real_fk
            if real_fk not in real_cols:
                real_cols.append(real_fk)
        else:
            if c not in real_cols:
                real_cols.append(c)

    # Cache the prepared FK statement once.
    fk_stmts = {}
    for c in cols:
        if c.startswith("_"):
            ref_table, ref_sql = fk_derefs[c]
            fk_stmts[c] = ref_sql

    select_sql = f"SELECT {','.join(real_cols)} FROM {table}"
    cursor = conn.execute(select_sql)

    real_idx = {c: i for i, c in enumerate(real_cols)}
    # For FK resolution use a separate connection cursor for lookups
    lookup_cur = conn.cursor()

    for row in cursor:
        # Build hash tuple in `cols` order
        hash_tuple = []
        for c in cols:
            if c.startswith("_"):
                real_fk = virtual_to_real[c]
                fk_val = row[real_idx[real_fk]]
                ref = lookup_cur.execute(fk_stmts[c], (fk_val,)).fetchone()
                hash_tuple.append(tuple(ref) if ref else None)
            else:
                hash_tuple.append(row[real_idx[c]])

        # Natural key tuple (subset of hash_tuple in `cols` order)
        nk_tuple = []
        for k in natural_key:
            idx = cols.index(k)
            nk_tuple.append(hash_tuple[idx])

        if book_id_col == "_global_":
            book_id = "_global_"
        else:
            book_id = row[real_idx[book_id_col]]

        yield book_id, tuple(nk_tuple), tuple(hash_tuple)


def stream_rows_dynamic(conn, table, book_id_col):
    cols = get_columns(conn, table)
    if not cols:
        return
    auto_id = detect_autoincrement_id(conn, table)
    if auto_id and auto_id in cols:
        cols = [c for c in cols if c != auto_id]
    if not cols:
        return
    select_sql = f"SELECT {','.join(cols)} FROM {table}"
    cursor = conn.execute(select_sql)
    real_idx = {c: i for i, c in enumerate(cols)}
    for row in cursor:
        if book_id_col == "_global_":
            book_id = "_global_"
        elif book_id_col in real_idx:
            book_id = row[real_idx[book_id_col]]
        else:
            book_id = "_global_"
        hash_tuple = tuple(row)
        nk_tuple = hash_tuple  # entire row is the key
        yield book_id, nk_tuple, hash_tuple


def snapshot_table(src_conn, snap_conn, table, spec):
    """Stream rows, compute hashes, write into snapshot DB. Returns (table_hash, row_count)."""
    is_dynamic = spec.get("_dynamic", False)
    book_id_col = spec["book_id_col"]
    if is_dynamic:
        natural_key_repr = "<dynamic>"
        row_iter = stream_rows_dynamic(src_conn, table, book_id_col)
    else:
        natural_key_repr = json.dumps(list(spec["natural_key"]))
        row_iter = stream_rows_explicit(src_conn, table, spec)

    # Accumulate per book in memory, flush each book when we transition.
    # Sort within-book during finalization.
    by_book = defaultdict(list)  # book_id -> list of (nk_tuple, row_hash)
    total_rows = 0
    for book_id, nk_tuple, hash_tuple in row_iter:
        rh = hash_row(hash_tuple)
        by_book[book_id].append((nk_tuple, rh))
        total_rows += 1

    if not by_book:
        return None, 0

    cur = snap_conn.cursor()
    book_hash_rows = []
    row_hash_rows = []
    for book_id, entries in by_book.items():
        # Stable sort by natural key
        entries.sort(key=lambda e: tuple("" if v is None else repr(v) for v in e[0]))
        sorted_hashes = [rh for _, rh in entries]
        bh = hash_group(sorted_hashes)
        book_hash_rows.append((table, book_id, bh, len(entries)))
        for nk_tuple, rh in entries:
            nk_json = json.dumps([str(v) if not isinstance(v, (int, float, type(None))) else v for v in nk_tuple], default=str)
            row_hash_rows.append((table, book_id, nk_json, rh))

    cur.executemany(
        "INSERT INTO book_hashes (table_name, book_id, book_hash, row_count) VALUES (?, ?, ?, ?)",
        book_hash_rows,
    )
    cur.executemany(
        "INSERT INTO row_hashes (table_name, book_id, natural_key_json, row_hash) VALUES (?, ?, ?, ?)",
        row_hash_rows,
    )

    table_hash = hash_group(sorted(r[2] for r in book_hash_rows))
    cur.execute(
        "INSERT INTO table_hashes (table_name, table_hash, natural_key, book_id_col, row_count) VALUES (?, ?, ?, ?, ?)",
        (table, table_hash, natural_key_repr, book_id_col, total_rows),
    )
    snap_conn.commit()
    return table_hash, total_rows


def snapshot(src_db_path, snap_db_path):
    src = sqlite3.connect(src_db_path)
    src.text_factory = str
    snap = sqlite3.connect(snap_db_path)
    snap.executescript(SCHEMA_SQL)
    snap.execute("PRAGMA journal_mode=WAL")
    snap.execute("PRAGMA synchronous=NORMAL")

    snap.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('source_db', ?)", (src_db_path,))
    snap.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('created_at', ?)", (time.strftime("%Y-%m-%dT%H:%M:%S"),))

    existing = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    table_hashes = []
    for table, spec in TABLES.items():
        if table not in existing:
            snap.execute("INSERT INTO skipped (table_name, reason) VALUES (?, ?)", (table, "table not in source"))
            continue
        sys.stderr.write(f"[merkle] snapshotting {table}...\n")
        sys.stderr.flush()
        t_start = time.time()
        th, rc = snapshot_table(src, snap, table, spec)
        if th is None:
            snap.execute("INSERT INTO skipped (table_name, reason) VALUES (?, ?)", (table, "empty/unparseable"))
            continue
        table_hashes.append(th)
        sys.stderr.write(f"[merkle]   {table}: {rc} rows, hash={th[:12]}..., {time.time()-t_start:.1f}s\n")

    # Catch unrecognized tables
    for name in existing:
        if name == "sqlite_sequence" or name in TABLES:
            continue
        snap.execute("INSERT INTO skipped (table_name, reason) VALUES (?, ?)", (name, "no spec; not snapshotted"))

    root_hash = hash_group(sorted(table_hashes))
    snap.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('root_hash', ?)", (root_hash,))
    snap.commit()
    snap.close()
    src.close()
    sys.stderr.write(f"[merkle] root_hash={root_hash}\n")


def diff_snapshots(before_path, after_path):
    """Walk the Merkle tree top-down: only descend into branches whose hash differs.

    Layer 0: root_hash (1 vs 1). If equal, return.
    Layer 1: table_hashes (12 vs 12). For each table where hashes differ, descend.
    Layer 2: book_hashes for that table. For each book where hashes differ, descend.
    Layer 3: row_hashes for that (table, book). Compare row by row.
    """
    b = sqlite3.connect(before_path)
    a = sqlite3.connect(after_path)

    b_root = b.execute("SELECT value FROM meta WHERE key='root_hash'").fetchone()[0]
    a_root = a.execute("SELECT value FROM meta WHERE key='root_hash'").fetchone()[0]
    print(f"Before snapshot: {before_path}")
    print(f"After  snapshot: {after_path}")
    print(f"Root hash before: {b_root}")
    print(f"Root hash after:  {a_root}")
    if b_root == a_root:
        print("\nROOT HASHES MATCH — no changes detected.")
        return 0
    print("\nROOT HASHES DIFFER — descending.\n")

    # Layer 1: table-level hashes (small: 12 rows each).
    b_tables = {row[0]: row for row in b.execute("SELECT table_name, table_hash, row_count FROM table_hashes")}
    a_tables = {row[0]: row for row in a.execute("SELECT table_name, table_hash, row_count FROM table_hashes")}
    all_tables = sorted(set(b_tables) | set(a_tables))

    differing_tables = 0
    for tname in all_tables:
        b_row = b_tables.get(tname)
        a_row = a_tables.get(tname)
        if b_row is None:
            print(f"+ TABLE {tname}: ADDED ({a_row[2]} rows)")
            differing_tables += 1
            continue
        if a_row is None:
            print(f"- TABLE {tname}: REMOVED (was {b_row[2]} rows)")
            differing_tables += 1
            continue
        if b_row[1] == a_row[1]:
            continue  # Merkle skip: identical, do not descend
        differing_tables += 1
        print(f"~ TABLE {tname}: changed (rows {b_row[2]} -> {a_row[2]})")

        # Layer 2: per-book hashes for THIS table only.
        b_books = {row[0]: row for row in b.execute(
            "SELECT book_id, book_hash, row_count FROM book_hashes WHERE table_name = ?",
            (tname,)
        )}
        a_books = {row[0]: row for row in a.execute(
            "SELECT book_id, book_hash, row_count FROM book_hashes WHERE table_name = ?",
            (tname,)
        )}
        all_books = sorted(set(b_books) | set(a_books))
        differing_books_in_table = 0
        for bk in all_books:
            bb = b_books.get(bk)
            ab = a_books.get(bk)
            if bb is None:
                differing_books_in_table += 1
                continue
            if ab is None:
                differing_books_in_table += 1
                continue
            if bb[1] != ab[1]:
                differing_books_in_table += 1
        print(f"   {differing_books_in_table} book group(s) differ (of {len(all_books)} total)")

        # Layer 3: per-row diff, only for books that actually differ.
        for bk in all_books:
            bb = b_books.get(bk)
            ab = a_books.get(bk)
            if bb is None:
                print(f"   + book {bk}: ADDED ({ab[2]} rows)")
                # List up to 5 added rows
                rows = b.execute("SELECT 1 LIMIT 0").fetchall()  # placeholder
                added_rows = a.execute(
                    "SELECT natural_key_json FROM row_hashes WHERE table_name = ? AND book_id = ? LIMIT 5",
                    (tname, bk)
                ).fetchall()
                for r in added_rows:
                    print(f"       + row key={r[0]}")
                if ab[2] > 5:
                    print(f"       ... +{ab[2]-5} more added")
                continue
            if ab is None:
                print(f"   - book {bk}: REMOVED (was {bb[2]} rows)")
                removed_rows = b.execute(
                    "SELECT natural_key_json FROM row_hashes WHERE table_name = ? AND book_id = ? LIMIT 5",
                    (tname, bk)
                ).fetchall()
                for r in removed_rows:
                    print(f"       - row key={r[0]}")
                if bb[2] > 5:
                    print(f"       ... +{bb[2]-5} more removed")
                continue
            if bb[1] == ab[1]:
                continue  # Merkle skip

            # Row-level diff: load only this book's rows from each side.
            b_rows = {}
            for nk, rh in b.execute(
                "SELECT natural_key_json, row_hash FROM row_hashes WHERE table_name = ? AND book_id = ?",
                (tname, bk)
            ):
                b_rows.setdefault(nk, []).append(rh)
            a_rows = {}
            for nk, rh in a.execute(
                "SELECT natural_key_json, row_hash FROM row_hashes WHERE table_name = ? AND book_id = ?",
                (tname, bk)
            ):
                a_rows.setdefault(nk, []).append(rh)

            all_nks = sorted(set(b_rows) | set(a_rows))
            changed_nks, added_nks, removed_nks = [], [], []
            for nk in all_nks:
                bl = sorted(b_rows.get(nk, []))
                al = sorted(a_rows.get(nk, []))
                if bl == al:
                    continue
                if not bl:
                    added_nks.append(nk)
                elif not al:
                    removed_nks.append(nk)
                else:
                    changed_nks.append(nk)

            print(f"   ~ book {bk}: {len(changed_nks)} changed, {len(added_nks)} added, {len(removed_nks)} removed")
            for nk in changed_nks[:5]:
                print(f"       ~ row key={nk}")
            if len(changed_nks) > 5:
                print(f"       ... +{len(changed_nks)-5} more changed")
            for nk in added_nks[:5]:
                print(f"       + row key={nk}")
            if len(added_nks) > 5:
                print(f"       ... +{len(added_nks)-5} more added")
            for nk in removed_nks[:5]:
                print(f"       - row key={nk}")
            if len(removed_nks) > 5:
                print(f"       ... +{len(removed_nks)-5} more removed")
        print()

    print(f"Summary: {differing_tables} table(s) differ.")
    b.close()
    a.close()
    return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "snapshot":
        if len(sys.argv) != 4:
            print("usage: merkle_snapshot.py snapshot <db_path> <snapshot_path>", file=sys.stderr)
            sys.exit(2)
        snapshot(sys.argv[2], sys.argv[3])
    elif cmd == "diff":
        if len(sys.argv) != 4:
            print("usage: merkle_snapshot.py diff <before.snap> <after.snap>", file=sys.stderr)
            sys.exit(2)
        sys.exit(diff_snapshots(sys.argv[2], sys.argv[3]))
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
