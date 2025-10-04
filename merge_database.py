#!/usr/bin/env python3
"""
Generic database merge script with proper AUTOINCREMENT foreign key handling.

This script correctly handles the translation_lookup -> translation_segments
foreign key relationship by tracking ID mappings during AUTOINCREMENT inserts.

Usage:
    python3 merge_database.py <source_db> <target_db>

Example:
    python3 merge_database.py persian/persian_texts.db data-prep/perseus_texts_sample.db
"""

import sqlite3
import sys
import os

def get_table_columns(cursor, table_name):
    """Get list of columns for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def has_autoincrement(cursor, table_name):
    """Check if table has AUTOINCREMENT primary key."""
    schema = cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
    if schema:
        return 'AUTOINCREMENT' in schema[0]
    return False

def merge_databases(source_db, target_db):
    """
    Merge source database into target database with proper ID mapping.

    Args:
        source_db: Path to source database
        target_db: Path to target database
    """

    # Verify databases exist
    if not os.path.exists(source_db):
        print(f"Error: Source database '{source_db}' not found")
        sys.exit(1)

    if not os.path.exists(target_db):
        print(f"Error: Target database '{target_db}' not found")
        sys.exit(1)

    print(f"Merging databases...")
    print(f"  Source: {source_db}")
    print(f"  Target: {target_db}")

    # Connect to both databases
    conn_src = sqlite3.connect(source_db)
    conn_tgt = sqlite3.connect(target_db)

    cur_src = conn_src.cursor()
    cur_tgt = conn_tgt.cursor()

    try:
        # Get list of tables from source (exclude sqlite internal tables)
        cur_src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [row[0] for row in cur_src.fetchall()]

        print(f"\nFound {len(tables)} tables to merge")

        # Track ID mappings for tables with AUTOINCREMENT
        id_mappings = {}

        # Process each table
        for table in tables:
            # Skip translation_lookup - we'll handle it after we have ID mappings
            if table == 'translation_lookup':
                continue

            # Check if table exists in target
            exists = cur_tgt.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                print(f"\nWarning: Table '{table}' exists in source but not in target. Skipping.")
                continue

            print(f"\nMerging table: {table}")

            # Get columns
            src_cols = get_table_columns(cur_src, table)
            tgt_cols = get_table_columns(cur_tgt, table)

            # Find common columns
            common_cols = [col for col in src_cols if col in tgt_cols]

            if not common_cols:
                print(f"  Warning: No common columns. Skipping.")
                continue

            # Check for AUTOINCREMENT
            is_autoincrement = has_autoincrement(cur_tgt, table)

            # Get row count
            count = cur_src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  Copying {count} rows...")

            if is_autoincrement:
                # For AUTOINCREMENT tables, exclude 'id' and track mappings
                cols_without_id = [col for col in common_cols if col.lower() != 'id']

                if not cols_without_id:
                    print(f"  Warning: Only 'id' column found. Skipping.")
                    continue

                # Check if this table has foreign keys pointing to it
                # (translation_segments is referenced by translation_lookup)
                needs_mapping = (table == 'translation_segments')

                if needs_mapping:
                    id_mappings[table] = {}
                    print(f"  Creating ID mapping for {table}...")

                # Build SELECT query
                select_cols = ', '.join(cols_without_id)
                cur_src.execute(f"SELECT id, {select_cols} FROM {table}")

                # Insert rows and track ID mappings
                inserted = 0
                for row in cur_src.fetchall():
                    old_id = row[0]
                    data = row[1:]

                    placeholders = ', '.join(['?' for _ in cols_without_id])
                    insert_sql = f"INSERT OR IGNORE INTO {table} ({select_cols}) VALUES ({placeholders})"

                    cur_tgt.execute(insert_sql, data)

                    if cur_tgt.rowcount > 0:
                        inserted += 1
                        if needs_mapping:
                            new_id = cur_tgt.lastrowid
                            id_mappings[table][old_id] = new_id

                print(f"  ✓ Inserted {inserted} rows")
                if needs_mapping and id_mappings[table]:
                    print(f"  ✓ Mapped IDs: {min(id_mappings[table].keys())}..{max(id_mappings[table].keys())} -> {min(id_mappings[table].values())}..{max(id_mappings[table].values())}")

            else:
                # For non-AUTOINCREMENT tables, insert all columns
                select_cols = ', '.join(common_cols)
                placeholders = ', '.join(['?' for _ in common_cols])

                cur_src.execute(f"SELECT {select_cols} FROM {table}")

                inserted = 0
                for row in cur_src.fetchall():
                    insert_sql = f"INSERT OR IGNORE INTO {table} ({select_cols}) VALUES ({placeholders})"
                    cur_tgt.execute(insert_sql, row)
                    if cur_tgt.rowcount > 0:
                        inserted += 1

                print(f"  ✓ Inserted {inserted} rows")

        # Special handling for translation_lookup - insert with corrected segment_ids
        if 'translation_lookup' in tables and 'translation_segments' in id_mappings:
            print(f"\nMerging translation_lookup with corrected segment_ids...")

            # Get the translation_lookup data from source
            cur_src.execute("SELECT book_id, line_number, segment_id FROM translation_lookup")
            lookup_rows = cur_src.fetchall()

            # Insert with corrected segment_ids (append-only)
            inserted = 0
            unmapped = 0
            for book_id, line_num, old_segment_id in lookup_rows:
                if old_segment_id in id_mappings['translation_segments']:
                    new_segment_id = id_mappings['translation_segments'][old_segment_id]
                    cur_tgt.execute("INSERT OR IGNORE INTO translation_lookup (book_id, line_number, segment_id) VALUES (?, ?, ?)",
                                   (book_id, line_num, new_segment_id))
                    if cur_tgt.rowcount > 0:
                        inserted += 1
                else:
                    unmapped += 1

            print(f"  ✓ Inserted {inserted} translation_lookup entries")
            if unmapped > 0:
                print(f"  ⚠ {unmapped} entries had unmapped segment_ids (skipped)")

        # Commit all changes
        conn_tgt.commit()

        # Verification
        print("\n=== Verification ===")

        # Show table counts
        for table in ['authors', 'works', 'books', 'text_lines', 'translation_segments', 'translation_lookup', 'words']:
            exists = cur_tgt.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if exists:
                count = cur_tgt.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  {table}: {count} rows")

        # Show authors by language if authors table exists
        exists = cur_tgt.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='authors'").fetchone()
        if exists:
            print("\nAuthors by language:")
            cur_tgt.execute("SELECT language, COUNT(*) FROM authors GROUP BY language ORDER BY language")
            for lang, count in cur_tgt.fetchall():
                print(f"  {lang}: {count}")

        print("\n✅ Merge completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during merge: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        conn_src.close()
        conn_tgt.close()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 merge_database.py <source_db> <target_db>")
        print("Example: python3 merge_database.py persian/persian_texts.db data-prep/perseus_texts_sample.db")
        sys.exit(1)

    source_db = sys.argv[1]
    target_db = sys.argv[2]

    merge_databases(source_db, target_db)
