#!/usr/bin/env python3
"""
Import Stephen Langdon's Sumerian Liturgies and Psalms into database.
Parses the Gutenberg text format to extract transliteration and translation pairs.
Creates intermediate CSV for debugging line duplication issues.
"""

import re
import csv
import sqlite3
import sys
from pathlib import Path

def parse_sumerian_text(file_path):
    """Parse Langdon's Sumerian text from Gutenberg format."""

    texts = []
    current_text = None
    current_lines = []
    sequence_number = 0  # Track actual sequence for database

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect text titles (all caps at start of line)
        if line and line[0].isupper() and ('LAMENTATION' in line or 'LITURGY' in line or
                                           'HYMN' in line or 'PSALM' in line):
            # Save previous text if exists
            if current_text and current_lines:
                current_text['lines'] = current_lines
                texts.append(current_text)
                current_lines = []
                sequence_number = 0  # Reset for new text

            # Start new text
            title = line.split('.')[0]  # Remove catalog number
            current_text = {
                'title': title,
                'type': 'liturgy' if 'LITURGY' in title else
                        'lamentation' if 'LAMENTATION' in title else
                        'hymn' if 'HYMN' in title else 'psalm'
            }

        # Parse numbered lines (transliteration and translation)
        elif re.match(r'^\d+\.', line):
            # This line has a number
            line_num_match = re.match(r'^(\d+)\.\s*(.*)', line)
            if line_num_match:
                source_line_number = int(line_num_match.group(1))  # Line number from source
                content = line_num_match.group(2)

                # Check if this is Sumerian (has underscores or special chars)
                is_sumerian = '_' in content or 'ģ' in content or 'ḫ' in content

                # Look for the matching translation on next numbered line
                if is_sumerian and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    next_match = re.match(r'^(\d+)\.\s*(.*)', next_line)

                    if next_match and int(next_match.group(1)) == source_line_number:
                        # We have a pair!
                        sumerian_text = content.replace('_', '').strip()
                        english_text = next_match.group(2).strip()

                        # Clean up footnote markers
                        sumerian_text = re.sub(r'\(\d+\)', '', sumerian_text)
                        english_text = re.sub(r'\(\d+\)', '', english_text)

                        if sumerian_text and english_text != '....':
                            sequence_number += 1  # Increment sequence for each actual line
                            current_lines.append({
                                'line_number': sequence_number,  # Use sequential numbering
                                'source_line_number': source_line_number,  # Keep original for reference
                                'sumerian': sumerian_text,
                                'translation': english_text
                            })
                        i += 1  # Skip the translation line

        i += 1

    # Save last text
    if current_text and current_lines:
        current_text['lines'] = current_lines
        texts.append(current_text)

    return texts

def export_to_csv(texts, csv_path='sumerian_texts.csv'):
    """Export parsed texts to CSV for debugging."""

    rows = []
    for text_idx, text_data in enumerate(texts, 1):
        if not text_data.get('lines'):
            continue

        for line in text_data['lines']:
            rows.append({
                'text_id': text_idx,
                'text_title': text_data['title'],
                'text_type': text_data['type'],
                'line_number': line['line_number'],
                'source_line_number': line.get('source_line_number', line['line_number']),
                'sumerian': line['sumerian'],
                'translation': line['translation']
            })

    # Write to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if rows:
            fieldnames = ['text_id', 'text_title', 'text_type', 'line_number', 'source_line_number', 'sumerian', 'translation']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Created {csv_path} with {len(rows)} lines")

    # Show summary statistics
    text_stats = {}
    for row in rows:
        text_id = row['text_id']
        if text_id not in text_stats:
            text_stats[text_id] = {
                'title': row['text_title'],
                'lines': []
            }
        text_stats[text_id]['lines'].append(row['line_number'])

    print("\nLines per text:")
    for text_id in sorted(text_stats.keys()):
        stats = text_stats[text_id]
        line_nums = sorted(set(stats['lines']))  # Remove duplicates and sort
        duplicates = len(stats['lines']) - len(line_nums)
        print(f"  Text {text_id} - {stats['title'][:40]}:")
        print(f"    Total entries: {len(stats['lines'])}, Unique lines: {len(line_nums)}")
        if duplicates > 0:
            print(f"    WARNING: {duplicates} duplicate line numbers detected!")
        if line_nums:
            print(f"    Line range: {min(line_nums)}-{max(line_nums)}")

    return rows

def import_to_database(db_path, texts):
    """Import parsed Sumerian texts into database."""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Add Langdon as author
    cur.execute('''
        INSERT OR REPLACE INTO authors (id, name, name_alt, language, has_translations)
        VALUES (?, ?, ?, ?, ?)
    ''', ('langdon_sumerian', 'Stephen Langdon (Sumerian Texts)',
          'Sumerian Liturgies', 'sumerian', 1))

    # Process each text
    for text_idx, text_data in enumerate(texts, 1):
        if not text_data.get('lines'):
            continue

        # Create work entry
        work_id = f'langdon_sumerian_{text_idx:03d}'
        cur.execute('''
            INSERT OR REPLACE INTO works
            (id, author_id, title, title_alt, title_english, type, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (work_id, 'langdon_sumerian', text_data['title'],
              text_data['title'], text_data['title'],
              text_data['type'], 'Stephen Langdon 1919, from Project Gutenberg'))

        # Create single book for this text
        book_id = f"{work_id}_text"
        line_count = len(text_data['lines'])

        cur.execute('''
            INSERT OR REPLACE INTO books
            (id, work_id, book_number, label, start_line, end_line, line_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (book_id, work_id, 1, text_data['title'],
              1, line_count, line_count))

        # Insert text lines and translations
        for i, line_data in enumerate(text_data['lines'], 1):
            # Insert Sumerian text
            cur.execute('''
                INSERT INTO text_lines
                (book_id, line_number, sequence_number, line_text)
                VALUES (?, ?, ?, ?)
            ''', (book_id, line_data['line_number'], i, line_data['sumerian']))

            # Insert translation if available
            if line_data.get('translation') and line_data['translation'] != '....':
                cur.execute('''
                    INSERT INTO translation_segments
                    (book_id, start_line, end_line, sequence_number,
                     translation_text, translator)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (book_id, line_data['line_number'], line_data['line_number'], i,
                      line_data['translation'], 'Stephen Langdon (1919)'))

                # Add to translation lookup
                segment_id = cur.lastrowid
                cur.execute('''
                    INSERT INTO translation_lookup
                    (book_id, line_number, segment_id)
                    VALUES (?, ?, ?)
                ''', (book_id, line_data['line_number'], segment_id))

            # Insert words for indexing
            words = line_data['sumerian'].split()
            for j, word in enumerate(words, 1):
                # Clean word - remove special markers
                word_clean = re.sub(r'[,.\[\]()!?]', '', word)
                if word_clean:
                    cur.execute('''
                        INSERT INTO words
                        (word, book_id, line_number, sequence_number, word_position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (word_clean, book_id, line_data['line_number'], i, j))

    conn.commit()

    # Report statistics
    cur.execute('SELECT COUNT(DISTINCT id) FROM works WHERE author_id = "langdon_sumerian"')
    work_count = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM text_lines WHERE book_id LIKE "langdon_sumerian%"')
    line_count = cur.fetchone()[0]

    conn.close()

    print(f"Successfully imported {work_count} Sumerian texts with {line_count} lines")
    return work_count, line_count

def main():
    if len(sys.argv) < 2:
        db_path = "sumerian_texts.db"
    else:
        db_path = sys.argv[1]

    # Load and parse the text
    text_file = Path("data-sources/langdon_sumerian/sumerian_liturgies_psalms.txt")

    if not text_file.exists():
        print(f"Error: {text_file} not found")
        print("Please run: python3 download_langdon_sumerian.py")
        sys.exit(1)

    print("Parsing Sumerian Liturgies and Psalms...")
    texts = parse_sumerian_text(text_file)

    print(f"Found {len(texts)} texts")
    for text in texts[:3]:  # Show first 3
        print(f"  - {text['title']}: {len(text.get('lines', []))} lines")

    # Export to CSV for debugging
    print("\nExporting to CSV for inspection...")
    rows = export_to_csv(texts)

    # Import to database
    print("\nImporting to database...")
    import_to_database(db_path, texts)

if __name__ == '__main__':
    main()