# merkle_snapshot.py — DB-build regression detector

A tool for catching unintended changes between two builds of any `perseus_texts_*.db`. Builds a hashed snapshot of a database, then a Merkle-style diff between two snapshots reveals **exactly** which rows changed.

Lives at `data-prep/merkle_snapshot.py`. Snapshot files are SQLite (separate utility DBs — they never touch the release `perseus_texts_*.db` and have no Room schema constraints).

---

## Why this exists

When changing the data-prep pipeline, the question is always: *did I change only what I intended, or did I quietly perturb something else?* Spot-check SQL queries catch known-target rows but miss collateral damage. Comparing two ~14 GB SQLite files byte-for-byte is meaningless — autoincrement `id` columns reshuffle every build.

The Merkle snapshot:
- Hashes each row by its **content**, not its ID
- Groups rows into per-book hashes, then per-table hashes, then a single root hash
- Diffs two snapshots top-down: if root hashes match, the DBs are equivalent (full stop). If they differ, the diff descends only into the branches that changed — so even ~50 M-row databases diff in seconds.

---

## Usage

### Snapshot a DB

```bash
python3 data-prep/merkle_snapshot.py snapshot <source_db> <snapshot_path>
```

Example:

```bash
python3 data-prep/merkle_snapshot.py snapshot \
    data-prep/perseus_texts_extended.db \
    /tmp/extended_before.snap
```

Reads the source DB, computes hashes for every relevant table+book+row, writes the result to `snapshot_path` (also a SQLite file).

Progress is logged to stderr per-table: `[merkle]   words: 49194205 rows, hash=cf68d58abd42..., 531.7s`. Final root hash is also logged.

### Diff two snapshots

```bash
python3 data-prep/merkle_snapshot.py diff <before.snap> <after.snap>
```

Exit code:
- `0` = root hashes match (no differences)
- `1` = root hashes differ (output describes them)

Output is a human-readable report: differing tables, then differing books per table, then differing rows per book (with the natural-key tuple identifying the row).

---

## How it works

### 3-tier Merkle tree

```
root_hash                    1 hash per DB
  └── table_hash             1 hash per data table (12 for the extended DB)
      └── book_hash          1 hash per (table, book_id) pair
          └── row_hash       1 hash per row, SHA-256 of canonicalized row content
```

Each parent hash is `SHA-256` of the sorted child hashes joined by `"\n"`. Sorting makes the tree order-independent: identical content always produces identical hashes regardless of insertion order.

### Snapshot DB schema

```sql
meta(key, value)                              -- source_db, created_at, root_hash
table_hashes(table_name, table_hash, ...)     -- 1 row per table
book_hashes(table_name, book_id,              -- 1 row per (table, book)
            book_hash, row_count)
row_hashes(table_name, book_id,               -- 1 row per source row
           natural_key_json, row_hash)
skipped(table_name, reason)                   -- tables in source DB but not snapshotted
```

Indexes on `row_hashes(table_name, book_id, ...)` make per-book lookup fast.

### Walk algorithm (the actually-Merkle part)

```python
if root_hash_before == root_hash_after:
    return "no changes"

for each table:
    if table_hash_before == table_hash_after:
        continue        # MERKLE SKIP — never touch this table's rows
    for each book in this table:
        if book_hash_before == book_hash_after:
            continue    # MERKLE SKIP — never touch this book's rows
        compare rows within this book by (natural_key, row_hash)
        emit added / removed / modified
```

This is the whole point: branches that match are skipped entirely. A 50 M-row DB where only 45 rows changed only ever loads ~45 rows for row-level comparison.

(An earlier implementation used SQL `FULL OUTER JOIN` at the row level — that defeats the Merkle structure and hangs at scale. The current implementation walks the tree top-down in Python.)

---

## What gets hashed

Tables in scope (defined in `TABLES` dict at the top of the script):

| Table | natural_key for row identification | book_id grouping |
|---|---|---|
| `authors` | `(id,)` | global |
| `works` | `(id,)` | global |
| `books` | `(id,)` | global |
| `text_lines` | `(book_id, sequence_number)` | `book_id` |
| `words` | `(book_id, line_number, sequence_number, word_position)` | `book_id` |
| `translation_segments` | `(book_id, translator, sequence_number)` | `book_id` |
| `translation_lookup` | `(book_id, line_number, segment_natural)` | `book_id` |
| `milestone_line_ranges` | dynamic (all non-id cols) | `book_id` |
| `lemma_map` | dynamic | global |
| `dictionary_entries` | dynamic | global |
| `normalization_patterns` | dynamic | global |
| `prefix_assimilation_rules` | dynamic | global |

### Excluded by design

- **Autoincrement `id` columns** — these shift between rebuilds (assignment order depends on insert ordering, which can drift for benign reasons). Snapshots use content-based identity instead.
- **`sqlite_sequence`** — Room/SQLite internal counter table.
- **Tables that don't exist in the source** — recorded in the `skipped` table for review.

### FK dereferencing

`translation_lookup.segment_id` references the autoincrement `translation_segments.id`. Hashing the raw int would make the lookup diff sensitive to id shifts. Instead, at snapshot time we dereference each `segment_id` via SQL to its natural-key tuple `(translator, sequence_number)`, so the lookup hash is stable when the underlying segment is unchanged.

### Dynamic tables

For tables without explicit specs (e.g., `lemma_map`), the script discovers columns at runtime and hashes all of them (minus any autoincrement id). The full row is the natural key. This is conservative but correct: any change is detected.

### Canonicalization rule

Each row's hashable form is the Python `repr()` of each column value, joined by `\x1f` (Unit Separator). This avoids ambiguity (e.g., `1` vs `"1"`, `None` vs `"None"`). The final `\n` join across rows uses sorted row hashes per book, sorted book hashes per table, sorted table hashes at root.

---

## What the diff output looks like

Typical diff after a targeted fix:

```
Root hash before: a5feeb9d820d1c946dc38a0a98da92ed7a26ee8fce3100fc1dc4f2ed97f6c550
Root hash after:  5c5dbf14b1c4ca12635f0616acdd3b1c9c2b4be9fd1bd655fa9d2ab5627a3bb4

ROOT HASHES DIFFER — descending.

~ TABLE translation_segments: changed (rows 3323753 -> 3323753)
   42 book group(s) differ (of 170305 total)
   ~ book tlg0007.tlg083.001: 1 changed, 0 added, 0 removed
       ~ row key=["tlg0007.tlg083.001", "Isaac Chauncy", 1]
   ...

~ TABLE translation_lookup: changed (rows 3912242 -> 3912663)
   41 book group(s) differ (of 169931 total)
   ~ book tlg0007.tlg083.001: 0 changed, 15 added, 0 removed
       + row key=["tlg0007.tlg083.001", 1, "('Isaac Chauncy', 1)"]
   ...

Summary: 3 table(s) differ.
```

How to read it:
- `~ TABLE X` — the table_hash for X differs.
- `~ book Y: N changed, M added, K removed` — Y's book_hash differs; N rows have the same natural key but different content, M rows are new in `after`, K rows existed only in `before`.
- `row key=[...]` — the natural-key tuple identifying that row. Use these as `WHERE` clauses to inspect the actual row content if you need to dig deeper.

Tables that don't appear in the output are byte-identical (their `table_hash` matched). For a 12-table DB where 9 tables match, you only see the 3 that changed.

---

## Performance

Measured on this machine (Apple Silicon, 1.8 TB disk):

| DB | Source size | Rows | Snapshot time | Snapshot size |
|---|---|---|---|---|
| `perseus_texts_sample.db` | 641 MB | 4.5 M | ~32 s | 2.1 GB |
| `perseus_texts_extended.db` | 13 GB | 73 M | ~15 min | 31 GB |

Diff time on the extended DB (one fix-shape change affecting 45 rows): **~3 seconds**. The Merkle walk skips ~99.99% of the rows.

---

## Limitations

1. **Snapshot files are big.** ~2× the size of the source DB because we store one row per source row plus per-row natural keys as JSON. Plan disk accordingly. (The extended DB needs ~50 GB free to hold two snapshots side-by-side.)

2. **Tables outside the `TABLES` dict aren't hashed.** If a future schema change adds a new data table, the script will mark it in `skipped` but not contribute it to the root hash. Currently the `TABLES` list matches the 12 data tables in `perseus_texts_extended.db` exactly. **Keep this list in sync with the source schema** when new tables are added to the build pipeline.

3. **Schema-level differences not detected.** The script hashes row content, not column types, indexes, triggers, or views. Room would refuse to open a DB with a schema mismatch anyway, but a purely additive index change wouldn't show up here.

4. **Empty tables are reported as skipped, not hashed.** If `normalization_patterns` is empty in one snapshot and populated in another, the diff catches it at the `table_hashes` level (one side has it, the other doesn't).

5. **Natural keys can have duplicates in source data.** For example, the Interlinear translator can produce multiple rows sharing `(book_id, translator, sequence_number)` when the source Greek line has multiple matching segments. The script handles this — `row_hashes` doesn't enforce uniqueness on natural_key; matching is by `(natural_key, row_hash)` tuple. If two rows share a natural key and one has its content modified, the diff reports it as one ADDED + one REMOVED at that natural key (cleaner than an ambiguous "MODIFIED" attribution).

---

## Typical workflow for verifying a data-prep fix

1. With unmodified pipeline, build the target DB from scratch:
   ```bash
   # for extended:
   greek/run_build.sh extended
   latin/run_build.sh extended
   # ... any other module DBs as needed ...
   python3 data-prep/assemble_database.py extended
   ```

2. Snapshot before:
   ```bash
   python3 data-prep/merkle_snapshot.py snapshot \
       data-prep/perseus_texts_extended.db \
       /tmp/extended_before.snap
   ```

3. Apply the fix. Rebuild module DBs that the fix affects. Re-assemble.

4. Snapshot after:
   ```bash
   python3 data-prep/merkle_snapshot.py snapshot \
       data-prep/perseus_texts_extended.db \
       /tmp/extended_after.snap
   ```

5. Diff:
   ```bash
   python3 data-prep/merkle_snapshot.py diff \
       /tmp/extended_before.snap \
       /tmp/extended_after.snap
   ```

6. Compare the diff against the fix's predicted regression contract. Every modified row should be one you intended to change. Every modified table should be one you expected to touch. Anything else is collateral.

Note: `dictionary_entries` always shows a single replaced row — the `build_time` metadata entry which records the build timestamp. That's expected noise and unrelated to the fix.

---

## Where it lives

- Code: `data-prep/merkle_snapshot.py`
- Documentation: `data-prep/MERKLE_SNAPSHOT.md` (this file)

Self-contained — no module dependencies beyond Python stdlib (`sqlite3`, `hashlib`, `json`).
