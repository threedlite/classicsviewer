# Database Merge Script

## Overview

This directory contains a generic `merge_database.py` script that correctly merges databases with AUTOINCREMENT foreign key references.

## Automatic Merging

**The main database build process automatically merges external databases based on build mode:**

### Build Modes:

1. **Sample** (`python3 create_perseus_database.py sample`)
   - **Merges:** Akkadian only (Gilgamesh)
   - **Reason:** Smallest database for Play Store release

2. **Full** (`python3 create_perseus_database.py full`)
   - **Merges:** Sumerian + Akkadian
   - **Reason:** All cuneiform languages for local debugging

3. **Extended** (`python3 create_perseus_database.py extended`)
   - **Merges:** Hebrew + Persian + Sumerian + Akkadian
   - **Reason:** Complete database with all available languages

The merges happen automatically after the Perseus database is built and before compression.

## The Problem

The original `merge_databases.sh` script had a critical bug when merging tables with AUTOINCREMENT primary keys that are referenced by other tables:

1. When inserting rows into a table with `AUTOINCREMENT PRIMARY KEY`, SQLite assigns new IDs
2. The old `merge_databases.sh` would insert `translation_segments` rows (getting new IDs)
3. Then it would insert `translation_lookup` rows with the OLD `segment_id` values
4. Result: `translation_lookup.segment_id` pointed to wrong translations (or non-existent rows)

**Example:**
- Source DB: `translation_segments` has IDs 1-4179
- Source DB: `translation_lookup.segment_id` references 1-4179
- Target DB: After merge, `translation_segments` gets NEW IDs 92042-96220
- Bug: `translation_lookup.segment_id` still contains 1-4179 (pointing to Greek text!)

## The Solution

`merge_database.py` fixes this by:

1. Tracking old_id → new_id mappings during AUTOINCREMENT table inserts
2. Detecting when `translation_lookup` needs foreign key updates
3. Updating `translation_lookup.segment_id` to use the new mapped IDs
4. Ensuring referential integrity

## Manual Usage (Advanced)

**NOTE:** Manual merging is rarely needed since `create_perseus_database.py` automatically merges based on build mode.

### When to Manually Merge:

- Testing merge functionality independently
- Custom database configurations
- Debugging merge issues

### Generic Script

```bash
python3 merge_database.py <source_db> <target_db>

# Example:
python3 merge_database.py persian/persian_texts.db data-prep/perseus_texts_sample.db
```

### Convenience Wrappers

Each language folder has a `merge_to_sample.sh` script for manual testing:

```bash
# Persian
cd persian
./merge_to_sample.sh

# Hebrew
cd hebrewOT
./merge_to_sample.sh

# Cuneiform (Sumerian/Akkadian)
cd cuneiform
./merge_to_sample.sh
```

**Warning:** Manual merges after the database build can cause issues if the database is already compressed.

## How It Works

1. **Iterates through all tables** in source database
2. **For non-AUTOINCREMENT tables**: Inserts all columns directly (e.g., `authors`, `works`, `books`)
3. **For AUTOINCREMENT tables**:
   - Excludes `id` column from INSERT
   - Lets SQLite generate new IDs
   - Tracks old_id → new_id mapping for `translation_segments`
4. **Special handling for translation_lookup**:
   - Detects if `translation_segments` was merged with ID mapping
   - Deletes old `translation_lookup` entries (with wrong IDs)
   - Re-inserts with corrected `segment_id` values using the mapping

## Tables Affected

### Tables with AUTOINCREMENT (IDs change during merge):
- `text_lines`
- `translation_segments` ← **Referenced by translation_lookup**
- `words`
- `dictionary_entries` (if present)

### Tables without AUTOINCREMENT (IDs preserved):
- `authors` (TEXT PRIMARY KEY)
- `works` (TEXT PRIMARY KEY)
- `books` (TEXT PRIMARY KEY)

### Foreign Key Table (requires correction):
- `translation_lookup` (has `segment_id` foreign key to `translation_segments.id`)

## Verification

The script performs verification after merge:

```
=== Verification ===
  authors: 14 rows
  works: 267 rows
  books: 674 rows
  text_lines: 262536 rows
  translation_segments: 100399 rows
  translation_lookup: 303873 rows
  words: 3822687 rows

Authors by language:
  akkadian: 1
  greek: 10
  latin: 2
  persian: 1
```

## Testing Translation Alignment

To verify translations work correctly after merge:

```python
import sqlite3

conn = sqlite3.connect('data-prep/perseus_texts_sample.db')
cur = conn.cursor()

# Test translation lookup
result = cur.execute("""
    SELECT ts.translation_text
    FROM translation_segments ts
    JOIN translation_lookup tl ON ts.id = tl.segment_id
    WHERE tl.book_id = 'hafez.divan.1' AND tl.line_number = 1
""").fetchone()

print(result[0])  # Should show correct Persian translation
```

## Migration Notes

**Old workflow (BROKEN):**
```bash
./merge_databases.sh source.db target.db
# Result: translation_lookup has wrong segment_ids
```

**New workflow (CORRECT):**
```bash
python3 merge_database.py source.db target.db
# Result: translation_lookup properly updated with new segment_ids
```

## Why the App Still Worked

The app uses a dual-query approach for translations:

```sql
SELECT DISTINCT ts.* FROM translation_segments ts
WHERE ts.book_id = :bookId
AND (
    -- Range-based lookup (THIS WORKED)
    (ts.start_line <= :endLine AND (ts.end_line IS NULL OR ts.end_line >= :startLine))
    OR
    -- Lookup table (THIS WAS BROKEN)
    EXISTS (...)
)
```

The **range-based query** (first condition) worked correctly, so translations appeared correct in the app despite the broken `translation_lookup` table.

The new merge script ensures **BOTH** methods work correctly.

## Files

- `/merge_database.py` - Generic merge script (root of repo)
- `/cuneiform/merge_to_sample.sh` - Cuneiform merge wrapper
- `/hebrewOT/merge_to_sample.sh` - Hebrew merge wrapper
- `/persian/merge_to_sample.sh` - Persian merge wrapper
- `/persian/merge_persian_to_sample.py` - Persian-specific version (deprecated, use generic script)

## Important Notes

- The script is **idempotent** - it uses `INSERT OR IGNORE` so running multiple times is safe
- For `translation_lookup`, it deletes and re-inserts to ensure correct IDs
- Always verify translations after merge using the test query above
- The old `merge_databases.sh` script should be considered **deprecated** for databases with translation_lookup tables

---

**Last Updated:** October 4, 2025
**Fixed Issue:** Translation_lookup foreign key corruption during AUTOINCREMENT merges
