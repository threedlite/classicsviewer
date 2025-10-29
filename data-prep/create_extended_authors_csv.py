#!/usr/bin/env python3
"""
Extract all authors and works from the extended database to create EXTENDED_AUTHORS.csv.
This file can be used as a starting point to create custom sample databases.
"""

import sqlite3
import csv
from pathlib import Path

def create_extended_authors_csv():
    """Extract all authors and works from extended database and create CSV."""

    db_path = Path("perseus_texts_extended.db")
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Please build the extended database first:")
        print("  python3 create_perseus_database.py extended")
        return

    print("Connecting to extended database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query all authors and works, ordered by author name then work title
    # Remove the _OGL suffix from work IDs for cleaner matching
    query = """
        SELECT DISTINCT
            a.name as author_name,
            w.title_english,
            w.id as work_id
        FROM authors a
        JOIN works w ON a.id = w.author_id
        ORDER BY a.name, w.title_english
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    print(f"Found {len(rows)} works from extended database")

    # Deduplicate: keep only unique author+work combinations
    # Some works exist in both Perseus and First1K
    unique_works = {}
    for author_name, work_title, work_id in rows:
        # Remove " (OGL)" suffix from First1K works for cleaner display
        clean_title = work_title.replace(" (OGL)", "")

        # Use (author, work) as key to deduplicate
        key = (author_name, clean_title)
        if key not in unique_works:
            unique_works[key] = (author_name, clean_title)

    print(f"After deduplication: {len(unique_works)} unique works")

    # Create CSV file matching SAMPLE_AUTHORS.csv style:
    # - Quote authors and work titles that contain spaces or special characters
    # - Don't quote single-word authors/titles
    csv_path = Path("EXTENDED_AUTHORS.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        # Write header
        csvfile.write('Author,Work\n')

        # Sort by author then work for consistency
        for (author_name, work_title) in sorted(unique_works.values()):
            # Quote author if it contains spaces or quotes
            if ' ' in author_name or '"' in author_name:
                escaped_author = author_name.replace('"', '""')
                author_field = f'"{escaped_author}"'
            else:
                author_field = author_name

            # Quote work title if it contains spaces or quotes
            if ' ' in work_title or '"' in work_title:
                escaped_title = work_title.replace('"', '""')
                work_field = f'"{escaped_title}"'
            else:
                work_field = work_title

            csvfile.write(f'{author_field},{work_field}\n')

    conn.close()

    print(f"\n✓ Created {csv_path}")
    print(f"  Total: {len(rows)} works")

    # Show some statistics
    cursor = sqlite3.connect(db_path).cursor()
    cursor.execute("SELECT COUNT(DISTINCT id) FROM authors")
    total_authors = cursor.fetchone()[0]
    print(f"  Authors: {total_authors}")

    # Count Perseus vs First1K works
    cursor.execute("SELECT COUNT(*) FROM works WHERE id LIKE '%_OGL'")
    first1k_count = cursor.fetchone()[0]
    perseus_count = len(rows) - first1k_count

    print(f"  Perseus works: {perseus_count}")
    print(f"  First1KGreek works: {first1k_count}")
    print(f"\nThis file can be edited to create custom sample databases.")
    print(f"To use it: python3 create_perseus_database.py sample EXTENDED_AUTHORS.csv")

if __name__ == "__main__":
    create_extended_authors_csv()
