#!/usr/bin/env python3
"""
Complete pipeline to process Akkadian texts from HTML to database.
Creates intermediate CSV for review, then populates database.
"""

import re
import csv
import sqlite3
import sys
from pathlib import Path

def parse_wikisource_to_csv():
    """Parse Wikisource pages and create CSV."""

    data_dir = Path("data-sources/wikisource_gilgamesh")

    if not data_dir.exists():
        print(f"Error: Data directory {data_dir} does not exist.")
        print("Please run download_wikisource_gilgamesh.py first.")
        return None

    # Combine all pages
    full_text = ""
    for page_file in sorted(data_dir.glob("page_*.txt")):
        with open(page_file, 'r', encoding='utf-8') as f:
            content = f.read()
            full_text += content + "\n"

    # Stop before "Second tablet"
    if 'duppu' in full_text and '2 kam-ma' in full_text:
        second_tablet_pos = full_text.find('duppu')
        full_text = full_text[:second_tablet_pos]

    lines = full_text.split('\n')

    # Track sections by number
    current_section = 1
    rows = []

    for i, line in enumerate(lines):
        # Check for any section marker and increment
        # Pattern can be {{c|{{larger|{{sc|...}}}}}} or variations
        if '{{c|{{larger|' in line and '{{sc|' in line:
            current_section += 1
            print(f"  Line {i}: Found section marker, now in Section {current_section}")
            continue

        # Parse table rows with transliteration
        if '||' in line and '{{hi|' in line:
            parts = line.split('||')

            if len(parts) >= 2:
                left_cell = parts[0]
                right_cell = parts[1]

                # Extract line number
                line_num_match = re.search(r'\{\{pline\|(\d+)\|', line)
                line_number = int(line_num_match.group(1)) if line_num_match else None

                # Extract transliteration - look for text within ''...''
                # First remove ref tags completely
                left_clean = re.sub(r'<ref[^>]*>.*?</ref>', '', left_cell)

                # Find text between '' markers
                translit_matches = re.findall(r"''([^']+?)''", left_clean)

                # If no '' markers, try to find text in {{hi|...}} directly
                if not translit_matches:
                    hi_match = re.search(r'\{\{hi\|[^|]+\|([^}]+)\}\}', left_cell)
                    if hi_match:
                        text = hi_match.group(1).strip()
                        # Remove HTML tags
                        text = re.sub(r'<sup>[^<]+</sup>', '', text)
                        text = re.sub(r'<[^>]+>', '', text)
                        if text:
                            translit_matches = [text]

                transliteration = ' '.join(translit_matches) if translit_matches else ""

                # Clean up transliteration
                transliteration = re.sub(r'<sup>([^<]+)</sup>', r'\1', transliteration)  # Keep superscript content
                transliteration = re.sub(r'<[^>]+>', '', transliteration)  # Remove other HTML
                transliteration = transliteration.strip()

                # Extract translation
                trans_match = re.search(r'\{\{hi\|[^|]+\|([^}]+)\}\}', right_cell)
                translation = ""
                if trans_match:
                    translation = trans_match.group(1).strip()
                    # Remove ref tags and their contents
                    translation = re.sub(r'<ref[^>]*>.*?</ref>', '', translation)
                    translation = translation.replace("''", "")

                if line_number and (transliteration or translation):
                    rows.append({
                        'section': current_section,
                        'line_number': line_number,
                        'transliteration': transliteration,
                        'translation': translation
                    })

    # Write to CSV
    csv_path = 'akkadian_texts.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['section', 'line_number', 'transliteration', 'translation'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created {csv_path} with {len(rows)} lines")

    # Show summary
    sections = {}
    for row in rows:
        if row['section'] not in sections:
            sections[row['section']] = []
        sections[row['section']].append(row['line_number'])

    print("\nLines per section:")
    for section_num in sorted(sections.keys()):
        line_nums = sections[section_num]
        print(f"  Section {section_num}: {len(line_nums)} lines (numbers {min(line_nums)}-{max(line_nums)})")

    return rows

def create_database(db_path):
    """Create Akkadian database with proper schema."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create schema matching perseus_texts_sample.db
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL,
            has_translations INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_alt TEXT,
            title_english TEXT,
            type TEXT,
            urn TEXT,
            description TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER NOT NULL,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            sequence_number INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS translation_lookup (
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            segment_id INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, segment_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_authors_language ON authors(language);
        CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id);
        CREATE INDEX IF NOT EXISTS idx_books_work ON books(work_id);
        CREATE INDEX IF NOT EXISTS idx_text_lines_book ON text_lines(book_id);
        CREATE INDEX IF NOT EXISTS idx_text_lines_sequence ON text_lines(book_id, sequence_number);
        CREATE INDEX IF NOT EXISTS idx_translation_segments_book ON translation_segments(book_id);
        CREATE INDEX IF NOT EXISTS idx_translation_segments_lines ON translation_segments(book_id, start_line);
        CREATE INDEX IF NOT EXISTS idx_words_word ON words(word);
        CREATE INDEX IF NOT EXISTS idx_words_book_line_seq ON words(book_id, line_number, sequence_number);
        CREATE INDEX IF NOT EXISTS index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number);
        CREATE INDEX IF NOT EXISTS index_translation_lookup_segment_id ON translation_lookup(segment_id);

        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;
    ''')

    conn.commit()
    return conn

def populate_database(conn, rows):
    """Populate database with parsed Akkadian text."""

    cur = conn.cursor()

    # Clear existing data
    cur.execute("DELETE FROM authors WHERE language = 'akkadian'")

    # Add Gilgamesh author
    cur.execute('''
        INSERT OR REPLACE INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('langdon_gilgamesh', 'Epic of Gilgamesh (Langdon 1917)',
          'Gilgamesh', 'akkadian', 1))

    # Create work entry
    work_id = 'gilgamesh_langdon_1917'
    cur.execute('''
        INSERT OR REPLACE INTO works
        (id, author_id, title, title_alt, title_english, type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (work_id, 'langdon_gilgamesh', 'Epic of Gilgamesh',
          'Gilgamish', 'Epic of Gilgamesh',
          'epic', 'Stephen Langdon 1917 translation and transliteration from Wikisource'))

    # Group rows by section
    sections_data = {}
    for row in rows:
        section = row['section']
        if section not in sections_data:
            sections_data[section] = []
        sections_data[section].append(row)

    # Section names for display
    section_labels = {
        1: 'Column I',
        2: 'Column II',
        3: 'Column III',
        4: 'Reverse I',
        5: 'Reverse II',
        6: 'Reverse III'
    }

    # Insert each section as a book
    for section_num in sorted(sections_data.keys()):
        section_lines = sections_data[section_num]
        book_id = f"{work_id}_{section_num:02d}"

        # Get line range
        line_numbers = [line['line_number'] for line in section_lines]
        start_line = min(line_numbers)
        end_line = max(line_numbers)
        line_count = len(set(line_numbers))  # Count unique line numbers

        # Insert book
        cur.execute('''
            INSERT OR REPLACE INTO books
            (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, section_num, section_labels.get(section_num, f'Section {section_num}'),
              start_line, end_line, line_count))

        # Insert text lines and translations
        for i, line_data in enumerate(section_lines, 1):
            # Insert transliterated text
            cur.execute('''
                INSERT INTO text_lines
                (book_id, line_number, sequence_number, line_text)
                VALUES (?, ?, ?, ?)
            ''', (book_id, line_data['line_number'], i, line_data['transliteration']))

            # Insert translation if available
            if line_data.get('translation'):
                cur.execute('''
                    INSERT INTO translation_segments
                    (book_id, start_line, end_line, sequence_number,
                     translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_id, line_data['line_number'], line_data['line_number'], i,
                      line_data['translation'], 'Stephen Langdon (1917)'))

                # Add to translation lookup
                segment_id = cur.lastrowid
                cur.execute('''
                    INSERT INTO translation_lookup
                    (book_id, line_number, segment_id)
                    VALUES (?, ?, ?)
                ''', (book_id, line_data['line_number'], segment_id))

            # Insert words for indexing
            words = line_data['transliteration'].split()
            for j, word in enumerate(words, 1):
                # Clean word - remove punctuation but keep hyphens
                word_clean = re.sub(r'[,.\[\]()]', '', word)
                if word_clean and word_clean != '{{gap}}':
                    cur.execute('''
                        INSERT INTO words
                        (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word_clean, book_id, line_data['line_number'], i, j))

        print(f"  Inserted {len(section_lines)} lines for {section_labels.get(section_num, f'Section {section_num}')}")

    conn.commit()
    print(f"\nSuccessfully populated database with {len(rows)} total lines")

def compress_database(db_path):
    """Compress database to ZIP file."""
    import subprocess

    zip_path = db_path + '.zip'
    print(f"\nCompressing database to {zip_path}...")

    # Remove old zip if exists
    Path(zip_path).unlink(missing_ok=True)

    # Create zip
    result = subprocess.run(['zip', '-9', zip_path, db_path],
                          capture_output=True, text=True)

    if result.returncode == 0:
        db_size = Path(db_path).stat().st_size / (1024 * 1024)
        zip_size = Path(zip_path).stat().st_size / (1024 * 1024)
        print(f"  Uncompressed: {db_size:.1f} MB")
        print(f"  Compressed: {zip_size:.1f} MB ({zip_size/db_size*100:.1f}%)")
        return True
    else:
        print(f"  Error compressing: {result.stderr}")
        return False

def main():
    """Main pipeline execution."""

    print("=" * 60)
    print("Akkadian Text Processing Pipeline")
    print("=" * 60)

    # Step 1: Parse HTML to CSV
    print("\n1. Parsing Wikisource HTML to CSV...")
    rows = parse_wikisource_to_csv()

    if not rows:
        print("Failed to parse Wikisource data")
        sys.exit(1)

    # Step 2: Create database
    db_path = "akkadian_texts.db"
    print(f"\n2. Creating database {db_path}...")

    # Remove old database if exists
    Path(db_path).unlink(missing_ok=True)

    conn = create_database(db_path)
    print("  Database schema created")

    # Step 3: Populate database
    print("\n3. Populating database from CSV...")
    populate_database(conn, rows)
    conn.close()

    # Step 4: Compress database
    print("\n4. Creating compressed version...")
    compress_database(db_path)

    print("\n" + "=" * 60)
    print("Processing complete!")
    print(f"  CSV: akkadian_texts.csv")
    print(f"  Database: {db_path}")
    print(f"  Compressed: {db_path}.zip")
    print("=" * 60)

if __name__ == '__main__':
    main()