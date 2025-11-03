#!/usr/bin/env python3
"""
Filter CLTK dictionary to keep only component lemmas found in extended database with definitions.

This script:
1. Loads the extended database dictionary entries (with definitions)
2. Reads the CLTK dictionary CSV from the ZIP file
3. For each compound decomposition, filters component lemmas to keep only those with definitions
4. Additionally removes any lemmas with 2 or fewer characters
5. Discards entries where either the left or right component group becomes empty
6. Discards entries where no components remain after filtering
7. Creates a new filtered dictionary ZIP file

Examples:
  Input:  "Compound parts possible matches: (x, y, abc) - (a, def, ghi)"
  If only abc, def, ghi have definitions in Perseus (and y, a are too short):
  Output: "Compound parts possible matches: (abc) - (def, ghi)"

  Input:  "Compound parts possible matches: (x, y) - (abc, def)"
  If only abc, def have definitions (and x, y are too short):
  Output: ENTRY DISCARDED (left group is empty)
"""

import sqlite3
import csv
import zipfile
import sys
import re
from pathlib import Path

def load_extended_db_lemmas(db_path):
    """Load all Greek lemmas from extended database that have definitions."""
    print(f"Loading lemmas with definitions from {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First check if dictionary_entries table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dictionary_entries'"
    )
    if not cursor.fetchone():
        print("ERROR: dictionary_entries table not found in database!")
        conn.close()
        return set()

    # Get all Greek headwords that have definitions
    cursor.execute("""
        SELECT DISTINCT headword
        FROM dictionary_entries
        WHERE language = 'greek'
        AND headword IS NOT NULL
        AND headword != ''
        AND (
            (entry_plain IS NOT NULL AND LENGTH(entry_plain) > 0)
            OR (entry_xml IS NOT NULL AND LENGTH(entry_xml) > 0)
            OR (entry_html IS NOT NULL AND LENGTH(entry_html) > 0)
        )
    """)

    lemmas = set(row[0].lower() for row in cursor.fetchall())
    conn.close()

    print(f"Loaded {len(lemmas):,} unique Greek lemmas with definitions")
    return lemmas

def extract_component_lemmas(definition_text):
    """Extract component lemmas from CLTK compound decomposition format.

    Example input: "Compound parts possible matches: (βατάνιον, βάταλος) - (οἴχομαι, νώ)"
    Returns: [(βατάνιον, βάταλος), (οἴχομαι, νώ)]
    """
    # Pattern: (lemma1, lemma2, ...) - (lemma3, lemma4, ...)
    # Extract all parenthesized groups
    groups = re.findall(r'\(([^)]+)\)', definition_text)

    if not groups:
        return []

    # Split each group by comma and clean up
    result = []
    for group in groups:
        lemmas = [lemma.strip() for lemma in group.split(',')]
        lemmas = [lemma for lemma in lemmas if lemma]  # Remove empty strings
        if lemmas:
            result.append(lemmas)

    return result

def filter_component_groups(component_groups, valid_lemmas):
    """Filter each component group to keep only valid lemmas.

    Args:
        component_groups: List of lemma lists, e.g., [['x', 'y', 'z'], ['a', 'b', 'c']]
        valid_lemmas: Set of lemmas with definitions

    Returns:
        Filtered groups, or None if:
        - All groups become empty, OR
        - There are exactly 2 groups and either one becomes empty (left or right)
    """
    filtered_groups = []

    for group in component_groups:
        # Filter lemmas in this group (case-insensitive)
        # Also exclude lemmas with 2 or fewer characters
        filtered_group = [
            lemma for lemma in group
            if lemma.lower() in valid_lemmas and len(lemma) > 2
        ]

        # Keep the group even if empty for now (we'll check below)
        filtered_groups.append(filtered_group)

    # If there are exactly 2 groups (standard compound: left - right)
    # and either is empty, reject the entire entry
    if len(filtered_groups) == 2:
        if not filtered_groups[0] or not filtered_groups[1]:
            return None

    # For other cases, remove empty groups and return
    filtered_groups = [g for g in filtered_groups if g]

    # Return None if no groups remain
    return filtered_groups if filtered_groups else None

def rebuild_definition(component_groups):
    """Rebuild the definition string from filtered component groups.

    Args:
        component_groups: List of lemma lists, e.g., [['y'], ['a', 'c']]

    Returns:
        "Compound parts possible matches: (y) - (a, c)"
    """
    parts = []
    for group in component_groups:
        parts.append(f"({', '.join(group)})")

    return "Compound parts possible matches: " + " - ".join(parts)

def filter_cltk_dictionary(input_zip_path, output_zip_path, valid_lemmas):
    """Filter CLTK dictionary to keep only entries with valid component lemmas."""
    print(f"\nReading CLTK dictionary from {input_zip_path}...")

    # Read the original dictionary
    with zipfile.ZipFile(input_zip_path, 'r') as zin:
        with zin.open('dictionary.csv') as f:
            text_wrapper = (line.decode('utf-8') for line in f)
            reader = csv.DictReader(text_wrapper)
            original_entries = list(reader)

    print(f"Original CLTK dictionary has {len(original_entries):,} entries")

    # Filter entries
    filtered_entries = []
    kept_count = 0
    dropped_count = 0
    modified_count = 0

    for entry in original_entries:
        definition = entry['definition']

        # Extract component lemmas
        component_groups = extract_component_lemmas(definition)

        if not component_groups:
            # No parseable components, drop entry
            dropped_count += 1
            continue

        # Filter components
        filtered_groups = filter_component_groups(component_groups, valid_lemmas)

        if not filtered_groups:
            # No valid components remain, drop entry
            dropped_count += 1
            continue

        # Check if we modified the definition
        original_component_count = sum(len(g) for g in component_groups)
        filtered_component_count = sum(len(g) for g in filtered_groups)

        if filtered_component_count < original_component_count:
            modified_count += 1

        # Rebuild definition with filtered components
        entry['definition'] = rebuild_definition(filtered_groups)
        filtered_entries.append(entry)
        kept_count += 1

    print(f"\nFiltering results:")
    print(f"  Kept: {kept_count:,} entries ({kept_count/len(original_entries)*100:.1f}%)")
    print(f"  Modified: {modified_count:,} entries (had some components filtered)")
    print(f"  Dropped: {dropped_count:,} entries ({dropped_count/len(original_entries)*100:.1f}%)")

    # Write filtered dictionary to new ZIP
    print(f"\nWriting filtered dictionary to {output_zip_path}...")

    # First, read the morphology.csv to include it in the output
    with zipfile.ZipFile(input_zip_path, 'r') as zin:
        morphology_data = zin.read('morphology.csv')

    # Create new ZIP with filtered dictionary and original morphology
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        # Write filtered dictionary
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['lemma', 'definition', 'language', 'source_name'])
        writer.writeheader()
        writer.writerows(filtered_entries)
        zout.writestr('dictionary.csv', output.getvalue())

        # Copy morphology unchanged
        zout.writestr('morphology.csv', morphology_data)

    print(f"✓ Created filtered dictionary: {output_zip_path}")

    # Show statistics
    input_size = Path(input_zip_path).stat().st_size / (1024 * 1024)
    output_size = Path(output_zip_path).stat().st_size / (1024 * 1024)
    print(f"\nFile sizes:")
    print(f"  Input:  {input_size:.2f} MB")
    print(f"  Output: {output_size:.2f} MB (saved {input_size - output_size:.2f} MB)")

def find_database():
    """Find the best available Perseus database (tries extended, full, sample)."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # Go up one level from cltk_poc to project root

    # Try in order: extended > full > sample
    # Look in both project root and data-prep directory
    candidates = [
        project_root / "perseus_texts_extended.db",
        project_root / "perseus_texts_full.db",
        project_root / "perseus_texts_sample.db",
        project_root / "data-prep" / "perseus_texts_extended.db",
        project_root / "data-prep" / "perseus_texts_full.db",
        project_root / "data-prep" / "perseus_texts_sample.db",
    ]

    for db_path in candidates:
        if db_path.exists() and db_path.stat().st_size > 1000:  # > 1KB means not empty
            return db_path

    return None

def main():
    # Paths
    script_dir = Path(__file__).parent

    # Find the database to use
    db_path = find_database()
    if not db_path:
        print("ERROR: No Perseus database found!")
        print("\nSearched locations:")
        print("  - ./perseus_texts_extended.db")
        print("  - ./perseus_texts_full.db")
        print("  - ./perseus_texts_sample.db")
        print("  - ./data-prep/perseus_texts_*.db")
        print("\nPlease build a database first:")
        print("  cd data-prep && python3 create_perseus_database.py extended")
        sys.exit(1)

    print(f"Using database: {db_path}")

    # Input/output paths
    # Since script is now in cltk_poc folder, input file is in same directory
    input_zip = script_dir / "SAMPLE_AUTHORS_GREEK_ONLY_dictionary.zip"

    if not input_zip.exists():
        print("ERROR: Input dictionary not found!")
        print(f"Expected location: {input_zip}")
        sys.exit(1)

    # Output in the same directory as input
    output_zip = script_dir / "SAMPLE_AUTHORS_GREEK_ONLY_dictionary_filtered.zip"

    # Load valid lemmas from database
    valid_lemmas = load_extended_db_lemmas(db_path)

    if not valid_lemmas:
        print("ERROR: No valid lemmas loaded from database!")
        sys.exit(1)

    # Filter the CLTK dictionary
    filter_cltk_dictionary(input_zip, output_zip, valid_lemmas)

    print("\n✓ Filtering complete!")

if __name__ == '__main__':
    main()
