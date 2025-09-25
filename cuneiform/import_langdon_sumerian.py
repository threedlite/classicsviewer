#!/usr/bin/env python3
"""
Import Stephen Langdon's Sumerian Liturgies and Psalms into database.
Parses the Gutenberg text format to extract transliteration and translation pairs.
"""

import re
import sqlite3
import sys
from pathlib import Path

def parse_sumerian_text(file_path):
    """Parse Langdon's Sumerian text from Gutenberg format."""

    texts = []
    current_text = None
    current_lines = []

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
                line_number = int(line_num_match.group(1))
                content = line_num_match.group(2)

                # Check if this is Sumerian (has underscores or special chars)
                is_sumerian = '_' in content or 'ģ' in content or 'ḫ' in content

                # Look for the matching translation on next numbered line
                if is_sumerian and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    next_match = re.match(r'^(\d+)\.\s*(.*)', next_line)

                    if next_match and int(next_match.group(1)) == line_number:
                        # We have a pair!
                        sumerian_text = content.replace('_', '').strip()
                        english_text = next_match.group(2).strip()

                        # Clean up footnote markers
                        sumerian_text = re.sub(r'\(\d+\)', '', sumerian_text)
                        english_text = re.sub(r'\(\d+\)', '', english_text)

                        if sumerian_text and english_text != '....':
                            current_lines.append({
                                'line_number': line_number,
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

    # Import to database
    import_to_database(db_path, texts)

if __name__ == '__main__':
    main()