#!/usr/bin/env python3
"""
Complete pipeline to process Sumerian texts from Gutenberg to database.
Creates intermediate CSV for review, then populates database.
Handles sections (COL. I, COL. II, OBVERSE, REVERSE, etc.) as separate books.
"""

import re
import csv
import sqlite3
import sys
from pathlib import Path

def parse_sumerian_to_csv():
    """Parse Langdon's Sumerian text and create CSV with proper section/book handling."""

    text_file = Path("data-sources/langdon_sumerian/sumerian_liturgies_psalms.txt")

    if not text_file.exists():
        print(f"Error: {text_file} not found")
        print("Please run: python3 download_langdon_sumerian.py")
        return None

    with open(text_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Process file sequentially
    texts = []
    current_text = None
    current_section = None
    current_lines = []
    sequence_number = 0

    # Track state for pairing
    waiting_for_pair = False
    pending_sumerian = None
    pending_line_num = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect text titles (all caps at start of line)
        if line and line[0].isupper() and ('LAMENTATION' in line or 'LITURGY' in line or
                                           'HYMN' in line or 'PSALM' in line):
            # Save any pending unpaired line
            if waiting_for_pair and pending_sumerian is not None:
                sequence_number += 1
                current_lines.append({
                    'line_number': sequence_number,
                    'source_line_number': pending_line_num,
                    'section': current_section or 'Text',
                    'sumerian': pending_sumerian,
                    'translation': ''  # No translation found
                })
                waiting_for_pair = False
                pending_sumerian = None
                pending_line_num = None

            # Save previous text if exists
            if current_text and current_lines:
                current_text['lines'] = current_lines
                texts.append(current_text)
                current_lines = []
                sequence_number = 0
                current_section = None

            # Start new text
            title = line.split('.')[0]  # Remove catalog number
            current_text = {
                'title': title,
                'type': 'liturgy' if 'LITURGY' in title else
                        'lamentation' if 'LAMENTATION' in title else
                        'hymn' if 'HYMN' in title else 'psalm'
            }

        # Detect section markers (COL. I, COL. II, OBVERSE, REVERSE, etc.)
        elif line and ('COL.' in line or 'OBVERSE' in line or 'REVERSE' in line or
                      'TABLET' in line or 'COLUMN' in line):
            # Save any pending unpaired line before section change
            if waiting_for_pair and pending_sumerian is not None:
                sequence_number += 1
                current_lines.append({
                    'line_number': sequence_number,
                    'source_line_number': pending_line_num,
                    'section': current_section or 'Text',
                    'sumerian': pending_sumerian,
                    'translation': ''
                })
                waiting_for_pair = False
                pending_sumerian = None
                pending_line_num = None

            # Update section
            current_section = line
            sequence_number = 0  # Reset for new section

        # Parse numbered lines
        elif re.match(r'^\d+\.', line):
            line_match = re.match(r'^(\d+)\.\s*(.*)', line)
            if line_match:
                line_num = int(line_match.group(1))
                content = line_match.group(2).strip()

                # Collect continuation lines
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    # Check if this is a continuation (indented, not a new numbered line)
                    if next_line.startswith('            ') and next_line.strip() and not re.match(r'^\d+\.', next_line.strip()):
                        content += ' ' + next_line.strip()
                        j += 1
                    else:
                        break
                i = j - 1  # Update position

                # Process based on pairing state
                if not waiting_for_pair:
                    # This should be Sumerian, wait for its translation
                    pending_sumerian = content.replace('_', '').strip()
                    pending_sumerian = re.sub(r'\(\d+\)', '', pending_sumerian)
                    pending_line_num = line_num
                    waiting_for_pair = True
                else:
                    # This should be the translation for the pending Sumerian
                    if line_num == pending_line_num:
                        # Matching pair found
                        translation = content.strip()
                        translation = re.sub(r'\(\d+\)', '', translation)

                        sequence_number += 1
                        current_lines.append({
                            'line_number': sequence_number,
                            'source_line_number': pending_line_num,
                            'section': current_section or 'Text',
                            'sumerian': pending_sumerian,
                            'translation': translation
                        })
                        waiting_for_pair = False
                        pending_sumerian = None
                        pending_line_num = None
                    else:
                        # Different line number - save pending and start new
                        sequence_number += 1
                        current_lines.append({
                            'line_number': sequence_number,
                            'source_line_number': pending_line_num,
                            'section': current_section or 'Text',
                            'sumerian': pending_sumerian,
                            'translation': ''  # No matching translation
                        })

                        # Start new pending
                        pending_sumerian = content.replace('_', '').strip()
                        pending_sumerian = re.sub(r'\(\d+\)', '', pending_sumerian)
                        pending_line_num = line_num
                        waiting_for_pair = True

        i += 1

    # Process any final pending line
    if waiting_for_pair and pending_sumerian is not None:
        sequence_number += 1
        current_lines.append({
            'line_number': sequence_number,
            'source_line_number': pending_line_num,
            'section': current_section or 'Text',
            'sumerian': pending_sumerian,
            'translation': ''
        })

    # Save last text
    if current_text and current_lines:
        current_text['lines'] = current_lines
        texts.append(current_text)

    # Convert to flat CSV format
    rows = []
    for text_idx, text_data in enumerate(texts, 1):
        if not text_data.get('lines'):
            continue

        for line in text_data['lines']:
            rows.append({
                'text_id': text_idx,
                'text_title': text_data['title'],
                'text_type': text_data['type'],
                'section': line['section'],
                'line_number': line['line_number'],
                'source_line_number': line.get('source_line_number', line['line_number']),
                'sumerian': line['sumerian'],
                'translation': line['translation']
            })

    # Write to CSV
    csv_path = 'sumerian_texts.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if rows:
            fieldnames = ['text_id', 'text_title', 'text_type', 'section',
                         'line_number', 'source_line_number', 'sumerian', 'translation']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Created {csv_path} with {len(rows)} lines")

    # Show summary statistics by text and section
    text_stats = {}
    for row in rows:
        text_id = row['text_id']
        section = row['section']
        if text_id not in text_stats:
            text_stats[text_id] = {
                'title': row['text_title'],
                'type': row['text_type'],
                'sections': {}
            }
        if section not in text_stats[text_id]['sections']:
            text_stats[text_id]['sections'][section] = []
        text_stats[text_id]['sections'][section].append(row['line_number'])

    print("\nLines per text and section:")
    total_books = 0
    for text_id in sorted(text_stats.keys()):
        stats = text_stats[text_id]
        print(f"  Text {text_id} - {stats['title'][:40]}:")
        for section in stats['sections']:
            line_nums = sorted(set(stats['sections'][section]))
            print(f"    {section}: {len(line_nums)} lines")
            total_books += 1

    print(f"\nTotal texts: {len(text_stats)}, Total books/sections: {total_books}")

    # Count lines with and without translations
    with_trans = sum(1 for r in rows if r['translation'])
    without_trans = sum(1 for r in rows if not r['translation'])
    print(f"Total lines: {len(rows)} ({with_trans} with translations, {without_trans} without)")

    return rows, text_stats

def create_database(db_path):
    """Create Sumerian database with proper schema."""

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

def populate_database(conn, rows, text_stats):
    """Populate database with parsed Sumerian text, creating separate books for each section."""

    cur = conn.cursor()

    # Clear existing data
    cur.execute("DELETE FROM authors WHERE language = 'sumerian'")

    # Add Langdon as author
    cur.execute('''
        INSERT OR REPLACE INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('langdon_sumerian', 'Stephen Langdon (Sumerian Texts)',
          'Sumerian Liturgies and Psalms', 'sumerian', 1))

    # Process each text
    for text_id in sorted(text_stats.keys()):
        stats = text_stats[text_id]

        # Create work entry
        work_id = f'langdon_sumerian_{text_id:03d}'
        cur.execute('''
            INSERT OR REPLACE INTO works
            (id, author_id, title, title_alt, title_english, type, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (work_id, 'langdon_sumerian', stats['title'],
              stats['title'], stats['title'],
              stats['type'], 'Stephen Langdon 1919, from Project Gutenberg'))

        # Create a book for each section
        book_num = 0
        for section_name in stats['sections']:
            book_num += 1
            book_id = f"{work_id}_book{book_num:02d}"

            # Get lines for this section
            section_lines = [r for r in rows if r['text_id'] == text_id and r['section'] == section_name]
            if not section_lines:
                continue

            # Get line range
            line_numbers = [r['line_number'] for r in section_lines]
            start_line = min(line_numbers)
            end_line = max(line_numbers)
            line_count = len(set(line_numbers))

            # Clean section name for label
            section_label = section_name.strip()
            if not section_label or section_label == 'Text':
                section_label = 'Main Text'

            cur.execute('''
                INSERT OR REPLACE INTO books
                (id, work_id, book_number, label, start_line, end_line, line_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (book_id, work_id, book_num, section_label,
                  start_line, end_line, line_count))

            # Insert text lines and translations for this section
            for row in section_lines:
                # Insert Sumerian text
                cur.execute('''
                    INSERT INTO text_lines
                    (book_id, line_number, sequence_number, line_text)
                    VALUES (?, ?, ?, ?)
                ''', (book_id, row['line_number'], row['line_number'], row['sumerian']))

                # Insert translation if available
                if row.get('translation'):
                    cur.execute('''
                        INSERT INTO translation_segments
                        (book_id, start_line, end_line, sequence_number,
                         translation_text, translator)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (book_id, row['line_number'], row['line_number'], row['line_number'],
                          row['translation'], 'Stephen Langdon (1919)'))

                    # Add to translation lookup
                    segment_id = cur.lastrowid
                    cur.execute('''
                        INSERT INTO translation_lookup
                        (book_id, line_number, segment_id)
                        VALUES (?, ?, ?)
                    ''', (book_id, row['line_number'], segment_id))

                # Insert words for indexing
                words = row['sumerian'].split()
                for j, word in enumerate(words, 1):
                    # Clean word - remove special markers
                    word_clean = re.sub(r'[,.\[\]()!?]', '', word)
                    if word_clean:
                        cur.execute('''
                            INSERT INTO words
                            (word, book_id, line_number, sequence_number, word_position)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (word_clean, book_id, row['line_number'], row['line_number'], j))

            print(f"  Inserted {len(section_lines)} lines for {stats['title'][:30]} - {section_label}")

    conn.commit()

    # Report statistics
    cur.execute('SELECT COUNT(DISTINCT id) FROM works WHERE author_id = "langdon_sumerian"')
    work_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(DISTINCT id) FROM books WHERE work_id LIKE "langdon_sumerian%"')
    book_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM text_lines WHERE book_id LIKE "langdon_sumerian%"')
    line_count = cur.fetchone()[0]

    print(f"\nSuccessfully populated database:")
    print(f"  Works: {work_count}")
    print(f"  Books (sections): {book_count}")
    print(f"  Lines: {line_count}")

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
    print("Sumerian Text Processing Pipeline")
    print("=" * 60)

    # Step 1: Parse text to CSV
    print("\n1. Parsing Sumerian Liturgies and Psalms to CSV...")
    result = parse_sumerian_to_csv()

    if not result:
        print("Failed to parse Sumerian data")
        sys.exit(1)

    rows, text_stats = result

    # Step 2: Create database
    db_path = "sumerian_texts.db"
    print(f"\n2. Creating database {db_path}...")

    # Remove old database if exists
    Path(db_path).unlink(missing_ok=True)

    conn = create_database(db_path)
    print("  Database schema created")

    # Step 3: Populate database
    print("\n3. Populating database from CSV...")
    populate_database(conn, rows, text_stats)
    conn.close()

    # Step 4: Compress database
    print("\n4. Creating compressed version...")
    compress_database(db_path)

    print("\n" + "=" * 60)
    print("Processing complete!")
    print(f"  CSV: sumerian_texts.csv")
    print(f"  Database: {db_path}")
    print(f"  Compressed: {db_path}.zip")
    print("=" * 60)

if __name__ == '__main__':
    main()